"""
Prompt file loader for ComfyUI-API-DockerCPU

- LoadPromptFromFile: pick a .txt file under input/prompts/ (subfolders
  included) from a dropdown and return its text.
- LoadCaptionPrompt: pick one caption row from a .csv / .parquet table under
  input/prompts/, optionally filtered on its metadata columns, with keyword
  replacement (e.g. the placeholder name "Alice" -> a LoRA trigger word).

Modelled on Inspire Pack's Load Prompts From File, but reads from the input
folder and returns the whole file as one string.
"""

import ast
import csv
import fnmatch
import hashlib
import json
import math
import os
import re
import sys

try:
    import folder_paths
    FOLDER_PATHS_AVAILABLE = True
except ImportError:
    FOLDER_PATHS_AVAILABLE = False

PROMPTS_SUBDIR = "prompts"
PROMPT_EXTENSIONS = {".txt"}
EXCLUDE_FOLDERS = {".*"}


def _prompts_dir():
    return os.path.join(folder_paths.get_input_directory(), PROMPTS_SUBDIR)


def _scan_prompt_files(base_dir, extensions=PROMPT_EXTENSIONS):
    """Relative (forward-slash) paths of every prompt file under base_dir,
    subfolders included, sorted alphabetically ignoring case."""
    files = []
    for root, dirs, names in os.walk(base_dir, followlinks=True):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, ex) for ex in EXCLUDE_FOLDERS)]
        for name in names:
            if os.path.splitext(name)[1].lower() not in extensions:
                continue
            rel = os.path.relpath(os.path.join(root, name), start=base_dir)
            files.append(rel.replace("\\", "/"))
    return sorted(files, key=lambda p: (p.casefold(), p))


def _resolve_prompt_file(prompt_file):
    """Absolute path of a prompt file, rejecting anything outside input/prompts/."""
    base = _prompts_dir()
    target = os.path.abspath(os.path.join(base, prompt_file.replace("\\", "/")))
    if not folder_paths.is_within_directory(base, target):
        raise ValueError(f"Invalid prompt file {prompt_file!r}: resolves outside of input/{PROMPTS_SUBDIR}/")
    return target


class LoadPromptFromFile:
    """
    Load a prompt from a text file in input/prompts/.

    The dropdown lists every .txt file under input/prompts/, subfolders
    included, in alphabetical order. Files are read as UTF-8 (a BOM is ignored).

    Outputs:
        text: The file's contents
    """

    @classmethod
    def INPUT_TYPES(cls):
        files = _scan_prompt_files(_prompts_dir()) if FOLDER_PATHS_AVAILABLE else []
        return {
            "required": {
                "prompt_file": (files, {"tooltip": f"Text file under input/{PROMPTS_SUBDIR}/. Press R to refresh the list."}),
            },
            "optional": {
                "reload": ("BOOLEAN", {"default": True, "label_on": "if file changed", "label_off": "if value changed",
                                       "tooltip": "On: re-read the file whenever its contents change. "
                                                  "Off: re-read only when a different file is selected."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = f"Loads a prompt from a .txt file in input/{PROMPTS_SUBDIR}/ (subfolders included)."

    def execute(self, prompt_file, reload=True):
        with open(_resolve_prompt_file(prompt_file), "r", encoding="utf-8-sig") as f:
            return (f.read(),)

    @classmethod
    def IS_CHANGED(cls, prompt_file, reload=True):
        if not reload:
            return prompt_file
        try:
            with open(_resolve_prompt_file(prompt_file), "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            return str(e)

    @classmethod
    def VALIDATE_INPUTS(cls, prompt_file):
        try:
            path = _resolve_prompt_file(prompt_file)
        except ValueError as e:
            return str(e)
        if not os.path.isfile(path):
            return f"Prompt file not found: input/{PROMPTS_SUBDIR}/{prompt_file}"
        return True


# ---------------------------------------------------------------------------
# Caption tables (.csv / .parquet)
# ---------------------------------------------------------------------------

CAPTION_EXTENSIONS = {".csv", ".parquet"}
ASPECT_RATIOS = ["any", "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "9:21", "21:9"]
NUDITY_OPTIONS = ["any", "none", "partial", "full", "partial or full"]

# Column names in the caption tables (matched case-insensitively)
COL_ASPECT = "aspect ratio"
COL_NUDITY = "nudity"
COL_LOCATION = "location"
COL_QUALITY = "artistic quality"
COL_EROTIC = "erotic score"
COL_PORN = "pornographic score"
COL_MALES = "males"
COL_FEMALES = "females"

_table_cache = {}  # abs path -> (mtime_ns, size, columns, rows); last 2 files kept
_TABLE_CACHE_MAX = 2


def _clean_value(value):
    """Normalise one cell: '' / NaN -> None, "['a', 'b']" -> ['a', 'b'],
    numeric strings -> int / float. Parquet values are already typed."""
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, SyntaxError):
            pass
        return value
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return value


def _read_csv(path):
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        rows = [{k: _clean_value(v) for k, v in row.items() if k is not None} for row in reader]
    return columns, rows


def _read_parquet(path):
    try:
        import pyarrow.parquet as pq
    except ImportError:
        pq = None
    if pq is not None:
        table = pq.read_table(path)
        columns = list(table.column_names)
        rows = [{k: _clean_value(v) for k, v in row.items()} for row in table.to_pylist()]
        return columns, rows
    try:
        import pandas as pd
    except ImportError as e:
        raise RuntimeError("Reading .parquet needs pyarrow (pip install pyarrow); or use the .csv version") from e
    df = pd.read_parquet(path)
    columns = [str(c) for c in df.columns]
    rows = []
    for rec in df.to_dict("records"):
        rows.append({str(k): _clean_value(v.tolist() if hasattr(v, "tolist") else v) for k, v in rec.items()})
    return columns, rows


def load_caption_table(path):
    """(columns, rows) of a .csv or .parquet caption table, cached until the file changes."""
    st = os.stat(path)
    key = os.path.normcase(os.path.abspath(path))
    cached = _table_cache.get(key)
    if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
        return cached[2], cached[3]
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        columns, rows = _read_csv(path)
    elif ext == ".parquet":
        columns, rows = _read_parquet(path)
    else:
        raise ValueError(f"Unsupported caption table {os.path.basename(path)!r}: use .csv or .parquet")
    _table_cache.pop(key, None)
    _table_cache[key] = (st.st_mtime_ns, st.st_size, columns, rows)
    while len(_table_cache) > _TABLE_CACHE_MAX:
        _table_cache.pop(next(iter(_table_cache)))
    return columns, rows


def parse_replacements(text):
    """'find = replace' pairs, one per line. Blank lines and lines starting
    with # are skipped; an empty right-hand side deletes the word."""
    pairs = []
    for number, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"replacements line {number} ({raw!r}): expected 'find = replace'")
        find, repl = line.split("=", 1)
        find, repl = find.strip(), repl.strip()
        if not find:
            raise ValueError(f"replacements line {number} ({raw!r}): nothing to find before '='")
        pairs.append((find, repl))
    return pairs


def apply_replacements(text, pairs, whole_word=True, case_sensitive=True):
    """Replace every 'find' with its 'replace' in one pass, so a replacement is
    never itself replaced again (Alice=Bella, Bella=Alice swaps them). Longer
    finds win over shorter ones that overlap. whole_word: 'Alice' matches in
    "Alice's" and "Alice," but not in "Alicent"."""
    if not pairs or not text:
        return text
    fold = (lambda s: s) if case_sensitive else str.casefold
    lookup = {}
    for find, repl in pairs:
        lookup[fold(find)] = repl  # later lines override earlier ones
    alternation = "|".join(re.escape(f) for f in sorted({f for f, _ in pairs}, key=len, reverse=True))
    pattern = f"(?<!\\w)(?:{alternation})(?!\\w)" if whole_word else f"(?:{alternation})"
    regex = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
    result = regex.sub(lambda m: lookup[fold(m.group(0))], text)
    if any(repl == "" for _, repl in pairs):
        result = re.sub(r"[ \t]{2,}", " ", result)
        result = re.sub(r"[ \t]+([,.;:!?])", r"\1", result)
        result = result.strip()
    return result


def _split_terms(text):
    return [t.strip().casefold() for t in (text or "").split(",") if t.strip()]


def _num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def filter_rows(columns, rows, caption_column="Caption", contains="", exclude="", aspect_ratio="any",
                nudity="any", location="", max_people=0, min_artistic_quality=0.0,
                max_erotic_score=1.0, max_pornographic_score=1.0):
    """Indices (into rows) of the rows that pass every filter. A filter left at
    its default is ignored; a filter set on a column the table lacks raises."""
    by_lower = {c.casefold(): c for c in columns}

    def col(name, needed):
        c = by_lower.get(name.casefold())
        if c is None and needed:
            raise ValueError(f"Caption table has no {name!r} column to filter on (columns: {', '.join(columns)})")
        return c

    cap = col(caption_column, True)
    want = _split_terms(contains)
    reject = _split_terms(exclude)
    c_aspect = col(COL_ASPECT, aspect_ratio != "any")
    c_nudity = col(COL_NUDITY, nudity != "any")
    locations = set(_split_terms(location))
    c_location = col(COL_LOCATION, bool(locations))
    c_males = col(COL_MALES, max_people > 0)
    c_females = col(COL_FEMALES, max_people > 0)
    c_quality = col(COL_QUALITY, min_artistic_quality > 0)
    c_erotic = col(COL_EROTIC, max_erotic_score < 1)
    c_porn = col(COL_PORN, max_pornographic_score < 1)
    nudity_ok = {"none": {None, "none"}, "partial": {"partial"}, "full": {"full"},
                 "partial or full": {"partial", "full"}}.get(nudity)

    keep = []
    for i, row in enumerate(rows):
        caption = row.get(cap)
        if not isinstance(caption, str) or not caption.strip():
            continue
        if want or reject:
            low = caption.casefold()
            if any(t not in low for t in want) or any(t in low for t in reject):
                continue
        if aspect_ratio != "any" and str(row.get(c_aspect) or "").strip() != aspect_ratio:
            continue
        if nudity_ok is not None:
            value = row.get(c_nudity)
            value = str(value).strip().casefold() if value is not None else None
            if value not in nudity_ok:
                continue
        if locations and str(row.get(c_location) or "").strip().casefold() not in locations:
            continue
        if max_people > 0:
            people = (_num(row.get(c_males)) or 0) + (_num(row.get(c_females)) or 0)
            if people > max_people:
                continue
        if min_artistic_quality > 0:
            q = _num(row.get(c_quality))
            if q is None or q < min_artistic_quality:
                continue
        if max_erotic_score < 1:
            q = _num(row.get(c_erotic))
            if q is None or q > max_erotic_score:
                continue
        if max_pornographic_score < 1:
            q = _num(row.get(c_porn))
            if q is None or q > max_pornographic_score:
                continue
        keep.append(i)
    return keep


def aspect_to_size(aspect_ratio, megapixels=1.0, multiple=16):
    """(width, height) for 'W:H' at about `megapixels`, each a multiple of `multiple`.
    Unparseable ratios give a square."""
    try:
        w, h = (float(p) for p in str(aspect_ratio).split(":"))
        if w <= 0 or h <= 0:
            raise ValueError
    except (ValueError, TypeError):
        w = h = 1.0
    area = max(megapixels, 0.01) * 1024 * 1024
    height = math.sqrt(area * h / w)
    width = height * w / h
    snap = lambda v: max(multiple, int(round(v / multiple)) * multiple)
    return snap(width), snap(height)


def _json_safe(value):
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    if hasattr(value, "item"):
        return value.item()
    return str(value)


class LoadCaptionPrompt:
    """
    Load one caption from a .csv / .parquet table in input/prompts/ as a prompt.

    Rows are filtered on the table's metadata columns, then `index` picks one of
    the remaining rows (wrapping around, so increment / randomize cycle through
    them). Keywords in the caption are then replaced, e.g. the placeholder
    "Alice" with a LoRA trigger word.

    Outputs:
        prompt: the caption after replacements
        original: the caption as stored in the file
        aspect_ratio: the row's aspect ratio ("" if the table has none)
        width / height: that aspect ratio at `megapixels`, multiples of 16
        row: the row's 0-based position in the file
        count: rows left after filtering
        metadata: the row's other columns as JSON
    """

    @classmethod
    def INPUT_TYPES(cls):
        files = _scan_prompt_files(_prompts_dir(), CAPTION_EXTENSIONS) if FOLDER_PATHS_AVAILABLE else []
        return {
            "required": {
                "caption_file": (files, {"tooltip": f".csv or .parquet table under input/{PROMPTS_SUBDIR}/. Press R to refresh the list."}),
                "index": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True,
                                  "tooltip": "Which of the filtered rows to use; wraps around the filtered count. "
                                             "Set the control to increment to walk through them, randomize to pick at random."}),
                "replacements": ("STRING", {"multiline": True, "default": "Alice = ohwx woman",
                                            "tooltip": "One 'find = replace' per line, e.g. 'Alice = ohwx woman'. "
                                                       "Empty right-hand side removes the word. Lines starting with # are ignored. "
                                                       "All lines apply in one pass, so swaps work."}),
            },
            "optional": {
                "whole_word": ("BOOLEAN", {"default": True, "tooltip": "Match whole words only: Alice matches \"Alice's\" but not \"Alicent\"."}),
                "case_sensitive": ("BOOLEAN", {"default": True}),
                "contains": ("STRING", {"default": "", "tooltip": "Keep captions containing every comma-separated term (case-insensitive, before replacement)."}),
                "exclude": ("STRING", {"default": "", "tooltip": "Drop captions containing any comma-separated term (e.g. Bella, Adam for solo shots)."}),
                "aspect_ratio": (ASPECT_RATIOS, {"default": "any"}),
                "nudity": (NUDITY_OPTIONS, {"default": "any", "tooltip": "'none' = empty Nudity cell."}),
                "location": ("STRING", {"default": "", "tooltip": "Comma-separated Location values to keep, e.g. 'bedroom, hotel room'. Empty = any."}),
                "max_people": ("INT", {"default": 0, "min": 0, "max": 20, "tooltip": "Most Males + Females in the row; 0 = any. 1 = solo shots."}),
                "min_artistic_quality": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "max_erotic_score": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "max_pornographic_score": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.05, "tooltip": "Size of the width / height outputs."}),
                "caption_column": ("STRING", {"default": "Caption"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("prompt", "original", "aspect_ratio", "width", "height", "row", "count", "metadata")
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = (f"Picks a caption from a .csv / .parquet table in input/{PROMPTS_SUBDIR}/, filtered on its metadata, "
                   "and replaces keywords such as a placeholder name with a trigger word.")

    def execute(self, caption_file, index, replacements, whole_word=True, case_sensitive=True, contains="", exclude="",
                aspect_ratio="any", nudity="any", location="", max_people=0, min_artistic_quality=0.0,
                max_erotic_score=1.0, max_pornographic_score=1.0, megapixels=1.0, caption_column="Caption"):
        pairs = parse_replacements(replacements)
        columns, rows = load_caption_table(_resolve_prompt_file(caption_file))
        keep = filter_rows(columns, rows, caption_column=caption_column, contains=contains, exclude=exclude,
                           aspect_ratio=aspect_ratio, nudity=nudity, location=location, max_people=max_people,
                           min_artistic_quality=min_artistic_quality, max_erotic_score=max_erotic_score,
                           max_pornographic_score=max_pornographic_score)
        if not keep:
            raise ValueError(f"No captions in {caption_file} match the filters ({len(rows)} rows in the file)")
        row_index = keep[index % len(keep)]
        row = rows[row_index]
        by_lower = {c.casefold(): c for c in columns}
        cap = by_lower[caption_column.casefold()]
        original = row[cap]
        prompt = apply_replacements(original, pairs, whole_word=whole_word, case_sensitive=case_sensitive)
        aspect_col = by_lower.get(COL_ASPECT)
        aspect = str(row.get(aspect_col) or "").strip() if aspect_col else ""
        width, height = aspect_to_size(aspect or "1:1", megapixels)
        metadata = json.dumps({k: _json_safe(v) for k, v in row.items() if k != cap}, ensure_ascii=False)
        return {"ui": {"text": [f"row {row_index} ({index % len(keep) + 1}/{len(keep)})"]},
                "result": (prompt, original, aspect, width, height, row_index, len(keep), metadata)}

    @classmethod
    def IS_CHANGED(cls, caption_file, **kwargs):
        try:
            st = os.stat(_resolve_prompt_file(caption_file))
            return f"{st.st_mtime_ns}:{st.st_size}"
        except Exception as e:
            return str(e)

    @classmethod
    def VALIDATE_INPUTS(cls, caption_file, replacements=None):
        try:
            path = _resolve_prompt_file(caption_file)
        except ValueError as e:
            return str(e)
        if os.path.splitext(path)[1].lower() not in CAPTION_EXTENSIONS:
            return f"Not a .csv or .parquet file: {caption_file}"
        if not os.path.isfile(path):
            return f"Caption file not found: input/{PROMPTS_SUBDIR}/{caption_file}"
        if replacements is not None:
            try:
                parse_replacements(replacements)
            except ValueError as e:
                return str(e)
        return True


NODE_CLASS_MAPPINGS = {
    "LoadPromptFromFile": LoadPromptFromFile,
    "LoadCaptionPrompt": LoadCaptionPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadPromptFromFile": "Load Prompt From File",
    "LoadCaptionPrompt": "Load Caption Prompt (CSV / Parquet)",
}
