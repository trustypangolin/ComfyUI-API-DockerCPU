"""
Image Load/Preview Utilities for ComfyUI-API-DockerCPU

Provides nodes for loading images with metadata extraction:
- LoadImageWithMetadata: Load an image from the input folder and extract
  embedded prompt, workflow, and EXIF metadata.
- LoadImageWithMetadataCrop: Same as above plus an optional crop region,
  returning both the cropped and original image along with a zoom factor.

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

try:
    from server import PromptServer
    from aiohttp import web
    ROUTES_AVAILABLE = True
except ImportError:
    PromptServer = None
    web = None
    ROUTES_AVAILABLE = False


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


def _scan_folder_files(base_dir):
    exclude_files = {
        "Thumbs.db",
        "*.DS_Store",
        "desktop.ini",
        "*.lock",
        "*.txt",
        "*.kra",
    }
    exclude_folders = {"clipspace", ".*"}

    file_list = []
    for root, dirs, files in os.walk(base_dir, followlinks=True):
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, ex) for ex in exclude_folders)]
        for file in files:
            if any(fnmatch.fnmatch(file, ex) for ex in exclude_files):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            relpath = os.path.relpath(os.path.join(root, file), start=base_dir)
            file_list.append(relpath.replace("\\", "/"))
    return sorted(file_list)


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


def _process_webp_exif(exif_data, metadata):
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


def _resolve_image_path(image, folder_type="input"):
    if folder_paths:
        if folder_type == "output":
            base_dir = folder_paths.get_output_directory()
            return os.path.join(base_dir, image)
        return folder_paths.get_annotated_filepath(image)
    return image


def _pil_to_tensor(image):
    if image.mode == "RGBA":
        bg = Image.new("RGBA", image.size, (0, 0, 0, 255))
        image = Image.alpha_composite(bg, image).convert("RGB")
    else:
        image = image.convert("RGB")
    arr = np.asarray(image).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None,]


def _pil_to_mask_tensor(image):
    if 'A' in image.getbands():
        mask = np.array(image.getchannel('A')).astype(np.float32) / 255.0
        mask = 1. - torch.from_numpy(mask)
    else:
        mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
    return mask.unsqueeze(0)


def _load_image_with_metadata(image_path, return_pil=False):
    """Open an image, extract metadata, and return tensors.

    Returns (pil_img, prompt, metadata, image_tensor, mask_tensor, width, height).
    If return_pil is False, pil_img is None.
    """
    img_f = Image.open(image_path)
    img_meta, prompt, metadata = _build_metadata(image_path)

    if img_f.format == 'WEBP' and PIEIXF_AVAILABLE:
        try:
            exif_data = piexif.load(image_path)
            prompt, metadata = _process_webp_exif(exif_data, metadata)
        except ValueError:
            prompt = {}

    img_meta = ImageOps.exif_transpose(img_meta)
    width, height = img_meta.size

    image_tensor = _pil_to_tensor(img_meta)
    mask_tensor = _pil_to_mask_tensor(img_meta)

    pil_img = img_meta if return_pil else None
    return pil_img, prompt, metadata, image_tensor, mask_tensor, width, height


def _clamp_crop_box(crop_x, crop_y, crop_w, crop_h, img_width, img_height):
    """Clamp a crop box to the image bounds.

    Returns (x, y, w, h) where x,y are ints in [0, dim-1] and w,h are >= 1.
    If any input is negative, the box spans the full image.
    """
    if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
        return 0, 0, img_width, img_height
    x = max(0, min(int(crop_x), img_width - 1))
    y = max(0, min(int(crop_y), img_height - 1))
    w = max(1, min(int(crop_w), img_width - x))
    h = max(1, min(int(crop_h), img_height - y))
    return x, y, w, h


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
                    "folder_type": (["input", "output"], {"default": "input", "tooltip": "Which ComfyUI folder to load from"}),
                },
            }

        input_files = _scan_folder_files(folder_paths.get_input_directory())

        return {
            "required": {
                "folder_type": (["input", "output"], {"default": "input", "tooltip": "Which ComfyUI folder to load from. The image dropdown is refreshed automatically."}),
                "image": (input_files, {"image_upload": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "JSON", "METADATA_RAW", "STRING", "STRING", "INT", "INT", "FLOAT")
    RETURN_NAMES = ("image", "mask", "prompt", "Metadata RAW", "BASE_FILENAME", "BASE_DIR", "height", "width", "megapixels")
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads an image from the input folder and extracts embedded prompt, workflow, and metadata."

    def execute(self, image, folder_type="input"):
        image_path = _resolve_image_path(image, folder_type)
        base_filename = Path(image_path).name
        base_dir = os.path.dirname(image_path)

        _, prompt, metadata, tensor, mask_tensor, width, height = _load_image_with_metadata(
            image_path
        )

        megapixels = round((width * height) / 1_000_000.0, 4)
        return tensor, mask_tensor, prompt, metadata, base_filename, base_dir, height, width, megapixels

    @classmethod
    def IS_CHANGED(cls, image, folder_type="input"):
        image_path = _resolve_image_path(image, folder_type)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image, folder_type="input"):
        image_path = _resolve_image_path(image, folder_type)
        if not os.path.isfile(image_path):
            return "Invalid image file: {}".format(image)
        return True


class LoadImageWithMetadataCrop:
    """
    Load an image with embedded metadata, then optionally crop a region.

    Behaves like LoadImageWithMetadata but also returns the original (uncropped)
    image tensor and a zoom factor (full-image diagonal / crop diagonal).
    A negative or zero crop dimension disables cropping and returns the full
    image as the cropped output with a zoom factor of 1.0.

    Outputs:
        image:             Cropped ComfyUI IMAGE tensor (BxHxWxC, float32, 0-1)
        mask:              Alpha mask tensor for the cropped region (1xHxW)
        original_image:    Full uncropped ComfyUI IMAGE tensor
        prompt:            JSON dict of the embedded ComfyUI prompt
        metadata:          Dict with file info, resolution, date, size, workflow, EXIF
        base_filename:     String filename without directory path
        base_dir:          String directory containing the image file
        crop_x:            Clamped X offset of the crop (INT)
        crop_y:            Clamped Y offset of the crop (INT)
        crop_width:        Clamped width of the crop (INT)
        crop_height:       Clamped height of the crop (INT)
        height:            Height of the cropped image (INT)
        width:             Width of the cropped image (INT)
        original_height:   Height of the source image before cropping (INT)
        original_width:    Width of the source image before cropping (INT)
        zoom_factor:       Ratio of full-image diagonal to crop diagonal (FLOAT)
        megapixels:        Cropped image megapixels (FLOAT)
    """

    @classmethod
    def INPUT_TYPES(cls):
        if not FOLDER_PATHS_AVAILABLE:
            return {
                "required": {
                    "image": ("STRING", {"default": "", "tooltip": "Path to image file"}),
                    "folder_type": (["input", "output"], {"default": "input", "tooltip": "Which ComfyUI folder to load from"}),
                },
                "optional": {
                    "crop_x": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Left edge of crop. -1 disables cropping."}),
                    "crop_y": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Top edge of crop. -1 disables cropping."}),
                    "crop_width": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop width. -1 disables cropping."}),
                    "crop_height": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop height. -1 disables cropping."}),
                },
            }

        input_files = _scan_folder_files(folder_paths.get_input_directory())

        return {
            "required": {
                "folder_type": (["input", "output"], {"default": "input", "tooltip": "Which ComfyUI folder to load from. The image dropdown is refreshed automatically."}),
                "image": (input_files, {"image_upload": True}),
            },
            "optional": {
                "crop_x": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Left edge of crop. -1 disables cropping."}),
                "crop_y": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Top edge of crop. -1 disables cropping."}),
                "crop_width": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop width. -1 disables cropping."}),
                "crop_height": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop height. -1 disables cropping."}),
            },
        }

    RETURN_TYPES = (
        "IMAGE", "MASK", "IMAGE",
        "JSON", "METADATA_RAW", "STRING", "STRING",
        "INT", "INT", "INT", "INT",
        "INT", "INT", "INT", "INT",
        "FLOAT", "FLOAT",
    )
    RETURN_NAMES = (
        "cropped_image", "mask", "original_image",
        "prompt", "Metadata RAW", "BASE_FILENAME", "BASE_DIR",
        "crop_x", "crop_y", "crop_width", "crop_height",
        "height", "width", "original_height", "original_width",
        "zoom_factor", "megapixels",
    )
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads an image with metadata and optionally crops a region, returning both the cropped and original images plus a zoom factor."

    def execute(self, image, folder_type="input", crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1):
        image_path = _resolve_image_path(image, folder_type)
        base_filename = Path(image_path).name
        base_dir = os.path.dirname(image_path)

        pil_img, prompt, metadata, original_tensor, _, orig_w, orig_h = _load_image_with_metadata(
            image_path, return_pil=True
        )

        x, y, w, h = _clamp_crop_box(crop_x, crop_y, crop_width, crop_height, orig_w, orig_h)
        cropped = pil_img.crop((x, y, x + w, y + h))
        cropped_tensor = _pil_to_tensor(cropped)
        cropped_mask = _pil_to_mask_tensor(cropped)

        # Zoom is the ratio between the full-image diagonal and crop diagonal.
        if x == 0 and y == 0 and w == orig_w and h == orig_h:
            zoom_factor = 1.0
        else:
            zoom_factor = float(np.hypot(orig_w, orig_h) / max(1e-9, np.hypot(w, h)))

        megapixels = round((w * h) / 1_000_000.0, 4)

        return (
            cropped_tensor, cropped_mask, original_tensor,
            prompt, metadata, base_filename, base_dir,
            x, y, w, h,
            h, w, orig_h, orig_w,
            zoom_factor, megapixels,
        )

    @classmethod
    def IS_CHANGED(cls, image, folder_type="input", crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1):
        image_path = _resolve_image_path(image, folder_type)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        m.update(f"|{crop_x},{crop_y},{crop_width},{crop_height}".encode())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image, folder_type="input", crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1):
        image_path = _resolve_image_path(image, folder_type)
        if not os.path.isfile(image_path):
            return "Invalid image file: {}".format(image)
        return True


NODE_CLASS_MAPPINGS = {
    "LoadImageWithMetadata": LoadImageWithMetadata,
    "LoadImageWithMetadataCrop": LoadImageWithMetadataCrop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageWithMetadata": "Load Image With Metadata",
    "LoadImageWithMetadataCrop": "Load Image with Metadata Crop",
}


if ROUTES_AVAILABLE:
    @PromptServer.instance.routes.get("/dockercpu/load_image_with_metadata/files")
    async def get_load_image_with_metadata_files(request):
        folder_type = request.query.get("folder_type", "input")
        if not FOLDER_PATHS_AVAILABLE:
            return web.json_response({"error": "folder_paths unavailable", "files": []}, status=400)
        if folder_type == "output":
            base_dir = folder_paths.get_output_directory()
        else:
            base_dir = folder_paths.get_input_directory()
        try:
            files = _scan_folder_files(base_dir)
            return web.json_response({"files": files, "folder_type": folder_type})
        except Exception as e:
            return web.json_response({"error": str(e), "files": []}, status=500)