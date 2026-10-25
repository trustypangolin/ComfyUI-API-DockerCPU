"""
Safe output paths for the filename-preserving savers.

Builds output/<stage>/<mirror_dir>/<filename> and refuses anything that
escapes the ComfyUI output directory or lands inside the input directory
(where the original scans live). Containment uses folder_paths.is_within_directory,
the same realpath check as native secure_subfolder_path.
"""

import os
import re

import folder_paths

IF_EXISTS_OPTIONS = ["error", "overwrite", "skip"]

# Windows drive letters ("C:"), UNC/absolute paths, and ".." segments are rejected outright,
# before the realpath containment checks.
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def clean_relative_dir(value, label):
    """Validate a relative folder ('01_isolate', '1992 Feb/sub') and return it
    with forward slashes. Empty means 'no subfolder'."""
    value = (value or "").replace("\\", "/").strip()
    if not value:
        return ""
    if value.startswith("/") or _DRIVE_RE.match(value):
        raise ValueError(f"{label} must be a relative folder, got {value!r}")
    parts = [p for p in value.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"{label} must not contain '..': {value!r}")
    return "/".join(parts)


def clean_name_part(value, label):
    """Validate a filename fragment (stem or suffix): no path separators."""
    value = value or ""
    if "/" in value or "\\" in value or _DRIVE_RE.match(value) or value in (".", ".."):
        raise ValueError(f"{label} must be a plain filename part, got {value!r}")
    return value


def assert_not_in_input(path):
    """Raise if path is anywhere under the ComfyUI input directory."""
    input_dir = folder_paths.get_input_directory()
    if folder_paths.is_within_directory(input_dir, path):
        raise ValueError(f"Refusing to write under the input directory ({input_dir}): {path}")


def stage_output_path(stage, mirror_dir, filename):
    """Absolute path output/<stage>/<mirror_dir>/<filename>, validated to be
    inside the output dir and outside the input dir."""
    output_dir = folder_paths.get_output_directory()
    stage = clean_relative_dir(stage, "stage")
    mirror_dir = clean_relative_dir(mirror_dir, "mirror_dir")
    filename = clean_name_part(filename, "filename")
    if not filename:
        raise ValueError("filename is empty")

    target = os.path.abspath(os.path.join(output_dir, stage, mirror_dir, filename))
    if not folder_paths.is_within_directory(output_dir, target):
        raise ValueError(f"Path resolves outside of the output directory: {target}")
    assert_not_in_input(target)
    return target


def write_atomic(path, write_func, if_exists):
    """Create parent dirs and write via write_func(tmp_path), then move into place.

    if_exists: 'error' raises if the file exists, 'skip' leaves it untouched,
    'overwrite' replaces it. Returns True if the file was written.
    """
    if if_exists not in IF_EXISTS_OPTIONS:
        raise ValueError(f"if_exists must be one of {IF_EXISTS_OPTIONS}, got {if_exists!r}")
    if os.path.exists(path):
        if if_exists == "skip":
            return False
        if if_exists == "error":
            raise FileExistsError(f"Output file already exists: {path} (set if_exists to overwrite or skip)")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{os.getpid()}.tmp"
    try:
        write_func(tmp_path)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return True
