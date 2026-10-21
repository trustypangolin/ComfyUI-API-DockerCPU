"""
Filename-preserving image saver for ComfyUI-API-DockerCPU

- SaveImageWithFilename: Writes output/<stage>/<mirror_dir>/<stem><suffix>.png
  with no counter, so pipeline stages mirror the original's folder and name.
  Refuses to write under the input directory (where the originals live).
"""

import json
import os

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths

from .output_paths import IF_EXISTS_OPTIONS, clean_name_part, stage_output_path, write_atomic

try:
    from comfy.cli_args import args as _comfy_args
except ImportError:
    _comfy_args = None


def _tensor_to_pil(image):
    # Round rather than truncate so an 8-bit source survives load -> save unchanged.
    arr = np.clip(np.round(image.cpu().numpy() * 255.0), 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _parse_extra_metadata(extra_metadata):
    if not extra_metadata or not extra_metadata.strip():
        return None
    try:
        return json.dumps(json.loads(extra_metadata))
    except json.JSONDecodeError as e:
        raise ValueError(f"extra_metadata is not valid JSON: {e}") from e


class SaveImageWithFilename:
    """
    Save images as output/<stage>/<mirror_dir>/<stem><suffix>.png, no counter.

    A batch of more than one image gets _00, _01, ... appended to each name.
    Embeds prompt/workflow like SaveImage (unless --disable-metadata or
    embed_workflow is off) and extra_metadata as the PNG tEXt key 'restore'.

    Outputs:
        saved_path: Absolute path(s) of the files, newline-separated for batches
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "stage": ("STRING", {"default": "00_test", "tooltip": "Top-level folder under output, e.g. 01_isolate."}),
                "mirror_dir": ("STRING", {"default": "", "tooltip": "Subfolder under the stage, e.g. MIRROR_DIR from the folder loader."}),
                "stem": ("STRING", {"default": "", "tooltip": "Filename without extension, e.g. STEM from the loader."}),
                "if_exists": (IF_EXISTS_OPTIONS, {"default": "error", "tooltip": "What to do when the file already exists."}),
                "embed_workflow": ("BOOLEAN", {"default": True, "tooltip": "Embed prompt and workflow like SaveImage."}),
            },
            "optional": {
                "suffix": ("STRING", {"default": "", "tooltip": "Appended to the stem, e.g. _p01_head."}),
                "extra_metadata": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional JSON stored as PNG text key 'restore'."}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Saves images to output/<stage>/<mirror_dir>/<stem><suffix>.png with no counter. Never writes into the input folder."

    def save_images(self, images, stage, mirror_dir, stem, if_exists="error", embed_workflow=True,
                    suffix="", extra_metadata="", prompt=None, extra_pnginfo=None):
        stem = clean_name_part(stem, "stem").strip()
        if not stem:
            raise ValueError("stem is empty; wire STEM from the loader or type a name")
        suffix = clean_name_part(suffix, "suffix")
        restore_text = _parse_extra_metadata(extra_metadata)

        batch = len(images)
        width = max(2, len(str(batch - 1)))
        names = [f"{stem}{suffix}.png"] if batch == 1 else [f"{stem}{suffix}_{i:0{width}d}.png" for i in range(batch)]
        # Resolve and check every target before writing anything, so a bad path or
        # an existing file in 'error' mode never leaves a partial batch behind.
        paths = [stage_output_path(stage, mirror_dir, name) for name in names]
        if if_exists == "error":
            for path in paths:
                if os.path.exists(path):
                    raise FileExistsError(f"Output file already exists: {path} (set if_exists to overwrite or skip)")

        metadata = PngInfo()
        if embed_workflow and not (_comfy_args is not None and _comfy_args.disable_metadata):
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for key in extra_pnginfo:
                    metadata.add_text(key, json.dumps(extra_pnginfo[key]))
        if restore_text is not None:
            metadata.add_text("restore", restore_text)

        output_dir = folder_paths.get_output_directory()
        results = []
        for image, path in zip(images, paths):
            img = _tensor_to_pil(image)
            write_atomic(path, lambda tmp: img.save(tmp, format="PNG", pnginfo=metadata, compress_level=4), if_exists)
            subfolder = os.path.relpath(os.path.dirname(path), output_dir).replace("\\", "/")
            results.append({"filename": os.path.basename(path), "subfolder": "" if subfolder == "." else subfolder, "type": "output"})

        return {"ui": {"images": results}, "result": ("\n".join(paths),)}


NODE_CLASS_MAPPINGS = {
    "SaveImageWithFilename": SaveImageWithFilename,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithFilename": "Save Image With Filename",
}
