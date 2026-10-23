"""
Restoration provenance: which PrimaryLibrary file an input image came from.

resolve_original(path) returns ("<album>/<file>", sha256 of the library file),
or ("", "") when it can't be determined. In order, stopping at the first that applies:
  1. The input PNG's 'restore' chunk has original + original_sha256: carry them,
     after confirming the library file's hash when the library is reachable.
  2. The chunk has only 'source' (an input-relative path): resolve that, recursively.
  3. The file is input/originals/<album>/<file> and the library twin has the same SHA-256.
When the library root is not reachable (the Docker deployment) only step 1 applies.

Only the single candidate library file is ever hashed: library files may be
OneDrive cloud-only placeholders that download when read.
"""

import hashlib
import json
import logging
import os
import re

from PIL import Image
from PIL.PngImagePlugin import PngImageFile

DEFAULT_LIBRARY_ROOT = "C:/Users/luton/OneDrive/Pictures/PrimaryLibrary"
LIBRARY_ENV = "PRIMARY_LIBRARY"
ORIGINALS_DIR = "originals"
MAX_SOURCE_DEPTH = 8

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_sha_cache = {}


def library_root(widget_value=""):
    """The library root: the widget value, else $PRIMARY_LIBRARY, else the default path."""
    return (widget_value or "").strip() or os.environ.get(LIBRARY_ENV, "").strip() or DEFAULT_LIBRARY_ROOT


def _sha256(path):
    # Keyed on size + mtime so a folder load (or a chain) hashes each file once.
    st = os.stat(path)
    key = (os.path.normcase(os.path.realpath(path)), st.st_size, st.st_mtime_ns)
    if key not in _sha_cache:
        m = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                m.update(chunk)
        _sha_cache[key] = m.hexdigest()
    return _sha_cache[key]


def _clean_rel(rel):
    """Forward-slash relative path, or None if it is absolute or climbs out with '..'."""
    rel = (rel or "").replace("\\", "/").strip()
    if not rel or rel.startswith("/") or _DRIVE_RE.match(rel):
        return None
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        return None
    return "/".join(parts)


def _real_case(root, rel):
    """rel with each segment spelled as on disk (Windows matches case-insensitively,
    the website pairs case-sensitively). None if a segment is missing. Lists folders only."""
    current, out = root, []
    for part in rel.split("/"):
        try:
            names = os.listdir(current)
        except OSError:
            return None
        match = part if part in names else next((n for n in names if n.casefold() == part.casefold()), None)
        if match is None:
            return None
        out.append(match)
        current = os.path.join(current, match)
    return "/".join(out) if os.path.isfile(current) else None


def _restore_chunk(path):
    """The parsed 'restore' PNG text chunk as a dict, or {}."""
    try:
        with Image.open(path) as img:
            if not isinstance(img, PngImageFile):
                return {}
            # .text (not .info) also sees text chunks written after IDAT, e.g. by backfill_restore_meta.py.
            raw = img.text.get("restore")
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _library_hash(lib_root, rel):
    """(real-case rel, sha256) of the library file, or (None, None) if it's missing or unreadable."""
    real = _real_case(lib_root, rel)
    if real is None:
        return None, None
    try:
        return real, _sha256(os.path.join(lib_root, real))
    except OSError as e:
        # e.g. a OneDrive placeholder that could not be downloaded
        logging.warning(f"[ComfyUI-API-DockerCPU] provenance: cannot read library file {real}: {e}")
        return None, None


def _input_rel(path, input_dir):
    """path relative to input_dir with forward slashes, or None if it lies outside."""
    real_input = os.path.realpath(input_dir)
    real_path = os.path.realpath(path)
    try:
        if os.path.commonpath([os.path.normcase(real_input), os.path.normcase(real_path)]) != os.path.normcase(real_input):
            return None
    except ValueError:  # different drives
        return None
    return os.path.relpath(real_path, real_input).replace("\\", "/")


def resolve_original(path, input_dir, lib_root, _depth=0):
    """(original, original_sha256) for the image at path, or ("", "")."""
    reachable = os.path.isdir(lib_root)
    restore = _restore_chunk(path) if os.path.isfile(path) else {}

    # 1. Carried provenance.
    original, sha = restore.get("original"), restore.get("original_sha256")
    if isinstance(original, str) and isinstance(sha, str) and original and sha:
        original, sha = _clean_rel(original), sha.lower()
        if original is None or not _SHA_RE.match(sha):
            return "", ""
        if not reachable:
            return original, sha
        real, lib_sha = _library_hash(lib_root, original)
        return (real, lib_sha) if lib_sha == sha else ("", "")

    if not reachable:
        return "", ""

    # 2. Older outputs record only the working input they were made from.
    source = restore.get("source")
    if isinstance(source, str) and source:
        source = _clean_rel(source.split(" [")[0])
        if source is None or _depth >= MAX_SOURCE_DEPTH:
            return "", ""
        source_path = os.path.join(input_dir, source)
        if _input_rel(source_path, input_dir) is None:
            return "", ""
        return resolve_original(source_path, input_dir, lib_root, _depth + 1)

    # 3. A byte copy of a library file under input/originals/.
    rel = _input_rel(path, input_dir)
    if rel is None or not rel.startswith(ORIGINALS_DIR + "/") or not os.path.isfile(path):
        return "", ""
    real, lib_sha = _library_hash(lib_root, rel[len(ORIGINALS_DIR) + 1:])
    if lib_sha is None:
        return "", ""
    try:
        same = _sha256(path) == lib_sha
    except OSError:
        return "", ""
    return (real, lib_sha) if same else ("", "")
