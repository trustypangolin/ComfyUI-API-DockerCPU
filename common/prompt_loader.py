"""
Prompt file loader for ComfyUI-API-DockerCPU

- LoadPromptFromFile: pick a .txt file under input/prompts/ (subfolders
  included) from a dropdown and return its text.

Modelled on Inspire Pack's Load Prompts From File, but reads from the input
folder and returns the whole file as one string.
"""

import fnmatch
import hashlib
import os

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


def _scan_prompt_files(base_dir):
    """Relative (forward-slash) paths of every prompt file under base_dir,
    subfolders included, sorted alphabetically ignoring case."""
    files = []
    for root, dirs, names in os.walk(base_dir, followlinks=True):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, ex) for ex in EXCLUDE_FOLDERS)]
        for name in names:
            if os.path.splitext(name)[1].lower() not in PROMPT_EXTENSIONS:
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


NODE_CLASS_MAPPINGS = {
    "LoadPromptFromFile": LoadPromptFromFile,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadPromptFromFile": "Load Prompt From File",
}
