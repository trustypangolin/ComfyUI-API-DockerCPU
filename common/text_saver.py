"""
Text File Saver for ComfyUI-API-DockerCPU

Provides a node to save text content to a file using a directory and
filename pair (typically from LoadImageWithMetadata). Useful for saving
sidecar text files (e.g., captions from a model API) next to source images.

- SaveTextWithFilename: Saves text to a file named after the source file.
"""

import os

from .output_paths import IF_EXISTS_OPTIONS, assert_not_in_input, clean_name_part, stage_output_path, write_atomic

OUTPUT_MODES = ["base_dir", "output_stage"]


class SaveTextWithFilename:
    """
    Save text content to a file.

    Modes:
        base_dir:      Writes into base_dir (legacy). Refused when base_dir is
                       under the input folder unless allow_input_dir is on.
        output_stage:  Writes output/<stage>/<mirror_dir>/<stem><suffix>.<extension>,
                       the same path rule as SaveImageWithFilename. stem defaults
                       to base_filename without its extension.

    Inputs:
        text:              The text content to save
        base_dir:          Directory where the file will be saved (base_dir mode)
        base_filename:     Source filename (used to derive the output name)
        replace_extension: If True, swap the source extension with `extension` (base_dir mode)
        extension:         New extension
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "forceInput": True}),
                "replace_extension": ("BOOLEAN", {"default": True}),
                "extension": ("STRING", {"default": "txt"}),
            },
            "optional": {
                "base_dir": ("STRING", {"forceInput": True}),
                "base_filename": ("STRING", {"forceInput": True}),
                "output_mode": (OUTPUT_MODES, {"default": "base_dir", "tooltip": "base_dir: write into base_dir. output_stage: write output/<stage>/<mirror_dir>/<stem><suffix>.<extension>."}),
                "stage": ("STRING", {"default": "", "tooltip": "output_stage mode: top-level folder under output."}),
                "mirror_dir": ("STRING", {"default": "", "tooltip": "output_stage mode: subfolder under the stage."}),
                "stem": ("STRING", {"default": "", "tooltip": "output_stage mode: filename without extension. Empty = base_filename without extension."}),
                "suffix": ("STRING", {"default": "", "tooltip": "output_stage mode: appended to the stem."}),
                "if_exists": (IF_EXISTS_OPTIONS, {"default": "overwrite", "tooltip": "What to do when the file already exists."}),
                "allow_input_dir": ("BOOLEAN", {"default": False, "tooltip": "base_dir mode: allow writing under the ComfyUI input folder."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save_text"
    OUTPUT_NODE = True
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Saves text to base_dir/base_filename, or to output/<stage>/<mirror_dir>/<stem><suffix>.<ext>. Refuses the input folder by default."

    def save_text(self, text, replace_extension=True, extension="txt", base_dir=None, base_filename=None,
                  output_mode="base_dir", stage="", mirror_dir="", stem="", suffix="",
                  if_exists="overwrite", allow_input_dir=False):
        ext = extension.strip().lstrip(".")

        if output_mode == "output_stage":
            stem = clean_name_part(stem, "stem").strip() or os.path.splitext(base_filename or "")[0]
            if not stem:
                raise ValueError("output_stage mode needs a stem or a base_filename")
            filename = f"{stem}{clean_name_part(suffix, 'suffix')}" + (f".{ext}" if ext else "")
            file_path = stage_output_path(stage, mirror_dir, filename)
        elif output_mode == "base_dir":
            if not base_dir or not base_filename:
                raise ValueError("base_dir mode needs base_dir and base_filename connected")
            name_without_ext = os.path.splitext(base_filename)[0]
            if replace_extension:
                final_filename = f"{name_without_ext}.{ext}" if ext else name_without_ext
            else:
                final_filename = base_filename
            file_path = os.path.join(base_dir, final_filename)
            if not allow_input_dir:
                assert_not_in_input(file_path)
        else:
            raise ValueError(f"Unknown output_mode: {output_mode!r}")

        def write(tmp_path):
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(text)

        write_atomic(file_path, write, if_exists)
        return (file_path,)


NODE_CLASS_MAPPINGS = {
    "SaveTextWithFilename": SaveTextWithFilename,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveTextWithFilename": "Save Text With Filename",
}
