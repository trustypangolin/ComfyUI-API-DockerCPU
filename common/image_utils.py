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
import re
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

from .provenance import library_root as _library_root, resolve_original

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

EXCLUDE_FILES = {
    "Thumbs.db",
    "*.DS_Store",
    "desktop.ini",
    "*.lock",
    "*.txt",
    "*.kra",
}
EXCLUDE_FOLDERS = {"clipspace", ".*"}

# Combo value that selects the input directory itself in the batch loader.
INPUT_ROOT_FOLDER = "."


def _is_excluded_folder(name):
    return any(fnmatch.fnmatch(name, ex) for ex in EXCLUDE_FOLDERS)


def _scan_folder_files(base_dir):
    file_list = []
    for root, dirs, files in os.walk(base_dir, followlinks=True):
        dirs[:] = [d for d in dirs if not _is_excluded_folder(d)]
        for file in files:
            if any(fnmatch.fnmatch(file, ex) for ex in EXCLUDE_FILES):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            relpath = os.path.relpath(os.path.join(root, file), start=base_dir)
            file_list.append(relpath.replace("\\", "/"))
    return sorted(file_list)


def _scan_subfolders(base_dir):
    """Relative (forward-slash) paths of every subfolder of base_dir, using the
    same folder exclusions as _scan_folder_files. The base itself is '.'."""
    folders = [INPUT_ROOT_FOLDER]
    for root, dirs, _files in os.walk(base_dir, followlinks=True):
        dirs[:] = [d for d in dirs if not _is_excluded_folder(d)]
        for d in dirs:
            relpath = os.path.relpath(os.path.join(root, d), start=base_dir)
            folders.append(relpath.replace("\\", "/"))
    return [INPUT_ROOT_FOLDER] + sorted(folders[1:], key=_natural_key)


def _natural_key(text):
    """Sort key that orders embedded numbers numerically: img2 < img10."""
    return [(0, int(part), "") if part.isdigit() else (1, 0, part.casefold())
            for part in re.split(r"(\d+)", text) if part]


def _file_sha256(path):
    m = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            m.update(chunk)
    return m.hexdigest()


def _input_rel_dir(image_path):
    """Directory of image_path relative to the input dir, forward slashes.

    '' when the file sits in the input root or lies outside the input dir
    (e.g. an annotated '[output]' path).
    """
    if not FOLDER_PATHS_AVAILABLE:
        return ""
    input_dir = folder_paths.get_input_directory()
    file_dir = os.path.dirname(os.path.abspath(image_path))
    if not folder_paths.is_within_directory(input_dir, file_dir):
        return ""
    rel = os.path.relpath(os.path.realpath(file_dir), os.path.realpath(input_dir)).replace("\\", "/")
    return "" if rel == "." else rel


def _strip_dir_prefix(rel_dir, prefix):
    """Remove a leading folder prefix ('originals/') from rel_dir, on whole
    path segments only. rel_dir is returned unchanged when it doesn't match."""
    prefix = prefix.replace("\\", "/").strip("/")
    if not prefix:
        return rel_dir
    if rel_dir == prefix:
        return ""
    if rel_dir.startswith(prefix + "/"):
        return rel_dir[len(prefix) + 1:]
    return rel_dir


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


def _resolve_image_path(image):
    if FOLDER_PATHS_AVAILABLE:
        return folder_paths.get_annotated_filepath(image)
    return image


LIBRARY_ROOT_INPUT = ("STRING", {"default": "", "tooltip": "PrimaryLibrary folder for ORIGINAL / ORIGINAL_SHA256. "
                                 "Empty = $PRIMARY_LIBRARY, else C:/Users/luton/OneDrive/Pictures/PrimaryLibrary."})


def _original(image_path, library_root):
    """(ORIGINAL, ORIGINAL_SHA256) for an input file: library '<album>/<file>' and its hash, or ('', '')."""
    input_dir = folder_paths.get_input_directory() if FOLDER_PATHS_AVAILABLE else os.getcwd()
    return resolve_original(image_path, input_dir, _library_root(library_root))


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
        height, width:   Image size after EXIF transpose (INT)
        megapixels:      Image megapixels (FLOAT)
        REL_DIR:         Directory relative to the input folder, forward slashes
        STEM:            Filename without extension
        SHA256:          Hex digest of the file bytes
        ORIGINAL:        PrimaryLibrary '<album>/<file>' this image derives from, or ''
        ORIGINAL_SHA256: Hex digest of that library file, or ''
    """

    @classmethod
    def INPUT_TYPES(cls):
        if not FOLDER_PATHS_AVAILABLE:
            return {
                "required": {
                    "image": ("STRING", {"default": "", "tooltip": "Path to image file"}),
                },
                "optional": {
                    "library_root": LIBRARY_ROOT_INPUT,
                },
            }

        input_files = _scan_folder_files(folder_paths.get_input_directory())

        return {
            "required": {
                "image": (input_files, {"image_upload": True}),
            },
            "optional": {
                "library_root": LIBRARY_ROOT_INPUT,
            },
        }

    # New outputs are appended only, so saved workflows keep their slot indices.
    RETURN_TYPES = ("IMAGE", "MASK", "JSON", "METADATA_RAW", "STRING", "STRING", "INT", "INT", "FLOAT",
                    "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "prompt", "Metadata RAW", "BASE_FILENAME", "BASE_DIR", "height", "width", "megapixels",
                    "REL_DIR", "STEM", "SHA256", "ORIGINAL", "ORIGINAL_SHA256")
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads an image from the input folder and extracts embedded prompt, workflow, and metadata."

    def execute(self, image, library_root=""):
        image_path = _resolve_image_path(image)
        base_filename = Path(image_path).name
        base_dir = os.path.dirname(image_path)

        _, prompt, metadata, tensor, mask_tensor, width, height = _load_image_with_metadata(
            image_path
        )

        megapixels = round((width * height) / 1_000_000.0, 4)
        return (tensor, mask_tensor, prompt, metadata, base_filename, base_dir, height, width, megapixels,
                _input_rel_dir(image_path), Path(image_path).stem, _file_sha256(image_path),
                *_original(image_path, library_root))

    @classmethod
    def IS_CHANGED(cls, image, library_root=""):
        image_path = _resolve_image_path(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        image_path = _resolve_image_path(image)
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
        REL_DIR:           Directory relative to the input folder, forward slashes
        STEM:              Filename without extension
        SHA256:            Hex digest of the file bytes
        ORIGINAL:          PrimaryLibrary '<album>/<file>' this image derives from, or ''
        ORIGINAL_SHA256:   Hex digest of that library file, or ''
    """

    @classmethod
    def INPUT_TYPES(cls):
        if not FOLDER_PATHS_AVAILABLE:
            return {
                "required": {
                    "image": ("STRING", {"default": "", "tooltip": "Path to image file"}),
                },
                "optional": {
                    "crop_x": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Left edge of crop. -1 disables cropping."}),
                    "crop_y": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Top edge of crop. -1 disables cropping."}),
                    "crop_width": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop width. -1 disables cropping."}),
                    "crop_height": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop height. -1 disables cropping."}),
                    "library_root": LIBRARY_ROOT_INPUT,
                },
            }

        input_files = _scan_folder_files(folder_paths.get_input_directory())

        return {
            "required": {
                "image": (input_files, {"image_upload": True}),
            },
            "optional": {
                "crop_x": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Left edge of crop. -1 disables cropping."}),
                "crop_y": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Top edge of crop. -1 disables cropping."}),
                "crop_width": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop width. -1 disables cropping."}),
                "crop_height": ("INT", {"default": -1, "min": -1, "max": 999999, "step": 1, "tooltip": "Crop height. -1 disables cropping."}),
                "library_root": LIBRARY_ROOT_INPUT,
            },
        }

    RETURN_TYPES = (
        "IMAGE", "MASK", "IMAGE",
        "JSON", "METADATA_RAW", "STRING", "STRING",
        "INT", "INT", "INT", "INT",
        "INT", "INT", "INT", "INT",
        "FLOAT", "FLOAT",
        "STRING", "STRING", "STRING",
        "STRING", "STRING",
    )
    RETURN_NAMES = (
        "cropped_image", "mask", "original_image",
        "prompt", "Metadata RAW", "BASE_FILENAME", "BASE_DIR",
        "crop_x", "crop_y", "crop_width", "crop_height",
        "height", "width", "original_height", "original_width",
        "zoom_factor", "megapixels",
        "REL_DIR", "STEM", "SHA256",
        "ORIGINAL", "ORIGINAL_SHA256",
    )
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads an image with metadata and optionally crops a region, returning both the cropped and original images plus a zoom factor."

    def execute(self, image, crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1, library_root=""):
        image_path = _resolve_image_path(image)
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
            _input_rel_dir(image_path), Path(image_path).stem, _file_sha256(image_path),
            *_original(image_path, library_root),
        )

    @classmethod
    def IS_CHANGED(cls, image, crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1, library_root=""):
        image_path = _resolve_image_path(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        m.update(f"|{crop_x},{crop_y},{crop_width},{crop_height}".encode())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image, crop_x=-1, crop_y=-1, crop_width=-1, crop_height=-1):
        image_path = _resolve_image_path(image)
        if not os.path.isfile(image_path):
            return "Invalid image file: {}".format(image)
        return True


def _resolve_input_folder(folder):
    """Absolute path of an input subfolder, rejecting anything that escapes the
    input dir (same containment check as native secure_subfolder_path)."""
    input_dir = folder_paths.get_input_directory()
    folder = (folder or INPUT_ROOT_FOLDER).replace("\\", "/")
    target = os.path.abspath(os.path.join(input_dir, folder))
    if not folder_paths.is_within_directory(input_dir, target):
        raise ValueError(f"Invalid folder {folder!r}: resolves outside of the input directory")
    return target


def _list_folder_images(folder, pattern, recursive):
    """Image paths (relative to the input dir, forward slashes) in natural order.

    Uses _scan_folder_files so exclusions match the single-image loader.
    The glob pattern is matched case-insensitively against the filename.
    """
    target = _resolve_input_folder(folder)
    if not os.path.isdir(target):
        raise FileNotFoundError(f"Input folder not found: {folder}")
    pattern = (pattern or "*").lower()
    folder_prefix = os.path.relpath(target, folder_paths.get_input_directory()).replace("\\", "/")

    files = []
    for rel in _scan_folder_files(target):
        if not recursive and "/" in rel:
            continue
        if not fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1].lower(), pattern):
            continue
        files.append(rel if folder_prefix == "." else f"{folder_prefix}/{rel}")
    return sorted(files, key=_natural_key)


class LoadImagesFromFolderWithMetadata:
    """
    Batch variant of LoadImageWithMetadata: loads every image in an input
    subfolder, in natural filename order, as lists (one entry per file).

    Images keep their native size, so outputs are lists rather than a batch
    tensor. Loading and EXIF transpose are shared with the single-image node.

    Outputs (all lists):
        image, mask:     Per-file IMAGE (1xHxWxC) and MASK tensors
        BASE_FILENAME:   Filename with extension
        STEM:            Filename without extension
        REL_DIR:         File's directory relative to the input folder
        MIRROR_DIR:      REL_DIR with strip_prefix removed ('originals/1990' -> '1990')
        SHA256:          Hex digest of the file bytes
        width, height:   Image size after EXIF transpose
        ORIGINAL:        PrimaryLibrary '<album>/<file>' each image derives from, or ''
        ORIGINAL_SHA256: Hex digest of that library file, or ''
    """

    @classmethod
    def INPUT_TYPES(cls):
        folders = _scan_subfolders(folder_paths.get_input_directory()) if FOLDER_PATHS_AVAILABLE else [INPUT_ROOT_FOLDER]
        return {
            "required": {
                "folder": (folders, {"tooltip": "Input subfolder to load. '.' is the input folder itself."}),
                "pattern": ("STRING", {"default": "*", "tooltip": "Filename glob, case-insensitive, e.g. *.jpg or img00*"}),
                "recursive": ("BOOLEAN", {"default": False, "tooltip": "Also load images from subfolders."}),
                "strip_prefix": ("STRING", {"default": "originals/", "tooltip": "Leading folder removed from REL_DIR to make MIRROR_DIR."}),
                "start_index": ("INT", {"default": 0, "min": 0, "max": 0xffffffff, "step": 1, "tooltip": "Skip this many files (after sorting)."}),
                "limit": ("INT", {"default": 0, "min": 0, "max": 0xffffffff, "step": 1, "tooltip": "Maximum files to load. 0 = all."}),
            },
            "optional": {
                "library_root": LIBRARY_ROOT_INPUT,
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING", "STRING", "STRING", "STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "BASE_FILENAME", "STEM", "REL_DIR", "MIRROR_DIR", "SHA256", "width", "height",
                    "ORIGINAL", "ORIGINAL_SHA256")
    OUTPUT_IS_LIST = (True,) * 11
    FUNCTION = "execute"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Loads all images in an input subfolder (natural order) as lists, with filename, folder and hash outputs for mirrored saving."

    @staticmethod
    def _select(folder, pattern, recursive, start_index, limit):
        files = _list_folder_images(folder, pattern, recursive)
        end = start_index + limit if limit > 0 else None
        return files[start_index:end]

    def execute(self, folder, pattern="*", recursive=False, strip_prefix="originals/", start_index=0, limit=0,
                library_root=""):
        files = self._select(folder, pattern, recursive, start_index, limit)
        if not files:
            raise ValueError(f"No images matched pattern {pattern!r} in input folder {folder!r} "
                             f"(recursive={recursive}, start_index={start_index}, limit={limit})")

        input_dir = folder_paths.get_input_directory()
        out = tuple([] for _ in self.RETURN_TYPES)
        for rel in files:
            image_path = os.path.join(input_dir, rel)
            _, _, _, tensor, mask_tensor, width, height = _load_image_with_metadata(image_path)
            rel_dir = rel.rsplit("/", 1)[0] if "/" in rel else ""
            values = (tensor, mask_tensor, Path(rel).name, Path(rel).stem, rel_dir,
                      _strip_dir_prefix(rel_dir, strip_prefix), _file_sha256(image_path), width, height,
                      *_original(image_path, library_root))
            for lst, value in zip(out, values):
                lst.append(value)
        return out

    @classmethod
    def IS_CHANGED(cls, folder, pattern="*", recursive=False, strip_prefix="originals/", start_index=0, limit=0,
                   library_root=""):
        # Cheap change detection: the selected file list plus each file's size and mtime.
        try:
            files = cls._select(folder, pattern, recursive, start_index, limit)
        except Exception as e:
            return str(e)
        input_dir = folder_paths.get_input_directory()
        m = hashlib.sha256(f"{strip_prefix}|".encode())
        for rel in files:
            st = os.stat(os.path.join(input_dir, rel))
            m.update(f"{rel}|{st.st_size}|{st.st_mtime_ns}\n".encode())
        return m.hexdigest()

    @classmethod
    def VALIDATE_INPUTS(cls, folder):
        try:
            target = _resolve_input_folder(folder)
        except ValueError as e:
            return str(e)
        if not os.path.isdir(target):
            return f"Input folder not found: {folder}"
        return True


NODE_CLASS_MAPPINGS = {
    "LoadImageWithMetadata": LoadImageWithMetadata,
    "LoadImageWithMetadataCrop": LoadImageWithMetadataCrop,
    "LoadImagesFromFolderWithMetadata": LoadImagesFromFolderWithMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadImageWithMetadata": "Load Image With Metadata",
    "LoadImageWithMetadataCrop": "Load Image with Metadata Crop",
    "LoadImagesFromFolderWithMetadata": "Load Images From Folder With Metadata",
}