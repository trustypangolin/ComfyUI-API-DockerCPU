"""
Image Load/Preview Utilities for ComfyUI-API-DockerCPU

Provides nodes for loading images with metadata extraction:
- LoadImageWithMetadata: Load an image from the input folder and extract
  embedded prompt, workflow, and EXIF metadata.

Adapted from ComfyUI-Crystools (CImageLoadWithMetadata).
"""

import fnmatch
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

import torch
import numpy as np
from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
from PIL.ExifTags import TAGS, GPSTAGS, IFD

try:
    import piexif
    PIEIXF_AVAILABLE = True
except ImportError:
    PIEIXF_AVAILABLE = False

try:
    import folder_paths
    FOLDER_PATHS_AVAILABLE = True
except ImportError:
    FOLDER_PATHS_AVAILABLE = False


def _get_size(path):
    size = os.path.getsize(path)
    if size < 1024:
        return f"{size} bytes"
    elif size < pow(1024, 2):
        return f"{round(size / 1024, 2)} KB"
    elif size < pow(1024, 3):
        return f"{round(size / (pow(1024, 2)), 2)} MB"
    elif size < pow(1024, 4):
        return f"{round(size / (pow(1024, 3)), 2)} GB"


def _build_metadata(image_path):
    if not Path(image_path).is_file():
        raise Exception(f"File not found: {image_path}")

    img = Image.open(image_path)

    metadata = {}
    prompt = {}

    metadata["fileinfo"] = {
        "filename": Path(image_path).as_posix(),
        "base_filename": Path(image_path).name,
        "resolution": f"{img.width}x{img.height}",
        "date": str(datetime.fromtimestamp(os.path.getmtime(image_path))),
        "size": str(_get_size(image_path)),
    }

    if isinstance(img, PngImageFile):
        metadata_from_img = img.info

        for k, v in metadata_from_img.items():
            if k == "workflow":
                try:
                    metadata["workflow"] = json.loads(v)
                except Exception:
                    pass

            elif k == "prompt":
                try:
                    metadata["prompt"] = json.loads(v)
                    prompt = metadata["prompt"]
                except Exception:
                    pass

            else:
                try:
                    metadata[str(k)] = json.loads(v)
                except Exception:
                    try:
                        metadata[str(k)] = str(v)
                    except Exception:
                        pass

    if isinstance(img, JpegImageFile):
        exif = img.getexif()

        for k, v in exif.items():
            tag = TAGS.get(k, k)
            if v is not None:
                metadata[str(tag)] = str(v)

        for ifd_id in IFD:
            try:
                if ifd_id == IFD.GPSInfo:
                    resolve = GPSTAGS
                else:
                    resolve = TAGS

                ifd = exif.get_ifd(ifd_id)
                ifd_name = str(ifd_id.name)
                metadata[ifd_name] = {}

                for k, v in ifd.items():
                    tag = resolve.get(k, k)
                    metadata[ifd_name][str(tag)] = str(v)

            except KeyError:
                pass

    return img, prompt, metadata


class LoadImageWithMetadata:
    """
    Load an image from the ComfyUI input folder with embedded metadata.

    Extracts prompt, workflow, and EXIF metadata from PNG/JPEG/WebP images.
    Returns the image tensor, alpha mask, prompt JSON, and full metadata dict.

    Outputs:
        image:           ComfyUI IMAGE tensor (BxHxWxC, float32, 0-1)
        mask:            Alpha mask tensor (1xHxW, float32, 0-1)
        prompt:          JSON dict of the embedded ComfyUI prompt
        metadata:        Dict with file info, resolution, date, size, workflow, EXIF
        base_filename:   String filename without directory path
        base_dir:        String directory containing the image file
    """

    @classmethod
    def INPUT_TYPES(cls):
        if not FOLDER_PATHS_AVAILABLE:
            return {
                "required": {
                    "image": ("STRING", {"default": "", "tooltip": "Path to image file"}),
                },
            }

        input_dir = folder_paths.get_input_directory()

        exclude_files = {"Thumbs.db", "*.DS_Store", "desktop.ini", "*.lock"}
        exclude_folders = {"clipspace", ".*"}

        file_list = []

        for root, dirs, files in os.walk(input_dir, followlinks=True):
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, exclude) for exclude in exclude_folders)]
            files = [f for f in files if not any(fnmatch.fnmatch(f, exclude) for exclude in exclude_files)]

            for file in files:
                relpath = os.path.relpath(os.path.join(root, file), start=input_dir)
                relpath = relpath.replace("\\", "/")
                file_list.append(relpath)

        return {
            "required": {
                "image": (sorted(file_list), {"image_upload": True})
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "JSON", "METADATA_RAW", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "prompt", "Metadata RAW", "BASE_FILENAME", "BASE_DIR")
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads an image from the input folder and extracts embedded prompt, workflow, and metadata."

    def execute(self, image):
        if folder_paths:
            image_path = folder_paths.get_annotated_filepath(image)
        else:
            image_path = image

        base_filename = Path(image_path).name
        base_dir = os.path.dirname(image_path)
        img_f = Image.open(image_path)
        img, prompt, metadata = _build_metadata(image_path)

        if img_f.format == 'WEBP' and PIEIXF_AVAILABLE:
            try:
                exif_data = piexif.load(image_path)
                prompt, metadata = self._process_webp_exif(exif_data, metadata)
            except ValueError:
                prompt = {}

        img = ImageOps.exif_transpose(img)
        image = img.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        if 'A' in img.getbands():
            mask = np.array(img.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        return image, mask.unsqueeze(0), prompt, metadata, base_filename, base_dir

    def _process_webp_exif(self, exif_data, metadata):
        if '0th' in exif_data and 271 in exif_data['0th']:
            prompt_data = exif_data['0th'][271].decode('utf-8')
            prompt_data = prompt_data.replace('Prompt:', '', 1)
            try:
                metadata['prompt'] = json.loads(prompt_data)
            except json.JSONDecodeError:
                metadata['prompt'] = prompt_data

        if '0th' in exif_data and 270 in exif_data['0th']:
            workflow_data = exif_data['0th'][270].decode('utf-8')
            workflow_data = workflow_data.replace('Workflow:', '', 1)
            try:
                metadata['workflow'] = json.loads(workflow_data)
            except json.JSONDecodeError:
                metadata['workflow'] = workflow_data

        metadata.update(exif_data)
        return metadata.get('prompt', {}), metadata

    @classmethod
    def IS_CHANGED(cls, image):
        if folder_paths:
            image_path = folder_paths.get_annotated_filepath(image)
        else:
            image_path = image
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if folder_paths:
            if not folder_paths.exists_annotated_filepath(image):
                return "Invalid image file: {}".format(image)
        elif not os.path.isfile(image):
            return "Invalid image file: {}".format(image)
        return True


NODE_CLASS_MAPPINGS = {
    "LoadImageWithMetadata": LoadImageWithMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageWithMetadata": "Load Image With Metadata",
}