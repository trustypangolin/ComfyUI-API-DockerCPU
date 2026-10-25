"""
Numbered bounding-box overlay for ComfyUI-API-DockerCPU (PIL only).

- DrawNumberedBBoxes: Draws each box with a legible number label, so faces can
  be referred to by position (1..N left to right) in surveys and downstream
  crops. Accepts the same BOUNDING_BOX shapes as native DrawBBoxes.
"""

import json

import numpy as np
import torch
from PIL import Image, ImageColor, ImageDraw, ImageFont

from .face_analysis import sort_left_to_right

SORT_OPTIONS = ["as_given", "left_to_right"]
# Bold fonts tried in order: Windows, then common Linux / Docker locations.
_FONT_CANDIDATES = ("arialbd.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arial.ttf")
AUTO_FONT_FRACTION = 0.025   # label text height as a fraction of the image's short edge
AUTO_LINE_FRACTION = 0.003   # box line width as a fraction of the short edge
MIN_FONT_PX = 14


def _load_font(size):
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1 has no sized default font
        return ImageFont.load_default()


def _contrast(rgb):
    """Black or white, whichever reads better on rgb."""
    r, g, b = rgb
    return (0, 0, 0) if 0.299 * r + 0.587 * g + 0.114 * b > 150 else (255, 255, 255)


def _per_frame(bboxes, batch):
    """Normalise to list[list[dict]] of length batch, as native DrawBBoxes does."""
    if isinstance(bboxes, dict):
        bboxes = [[bboxes]]
    elif not isinstance(bboxes, list) or not bboxes:
        bboxes = [[]]
    elif isinstance(bboxes[0], dict):
        bboxes = [bboxes]  # flat list -> same boxes on every image
    if len(bboxes) == 1:
        bboxes = bboxes * batch
    return [list(frame) for frame in (bboxes + [[]] * batch)[:batch]]


def _draw_frame(img, boxes, start_index, line_width, font_px, color, show_score):
    draw = ImageDraw.Draw(img)
    font = _load_font(font_px)
    halo = _contrast(color)
    pad = max(2, font_px // 6)
    W, H = img.size

    for n, b in enumerate(boxes):
        x1, y1 = float(b["x"]), float(b["y"])
        x2, y2 = x1 + float(b["width"]), y1 + float(b["height"])
        # Contrasting halo under the coloured line keeps it visible on dark and light scans.
        draw.rectangle([x1, y1, x2, y2], outline=halo, width=line_width + 2)
        draw.rectangle([x1 + 1, y1 + 1, x2 - 1, y2 - 1], outline=color, width=line_width)

        text = str(start_index + n)
        if show_score and "score" in b:
            text += f" {float(b['score']):.2f}"
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        tw, th = right - left, bottom - top
        lw, lh = tw + 2 * pad, th + 2 * pad

        # Label above the box, or inside its top edge when there's no room above.
        ly = y1 - lh if y1 - lh >= 0 else y1
        lx = min(max(0.0, x1), max(0.0, W - lw))
        draw.rectangle([lx, ly, lx + lw, ly + lh], fill=color, outline=halo, width=1)
        draw.text((lx + pad - left, ly + pad - top), text, font=font, fill=halo)
    return img


class DrawNumberedBBoxes:
    """
    Draw bounding boxes with a number label on each (1..N by default).

    Outputs:
        image:        Images with boxes and labels drawn
        bboxes:       BOUNDING_BOX list per frame, in drawn (numbered) order
        labels_json:  JSON list of {frame, index, x, y, width, height[, score]} (STRING)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "bboxes": ("BOUNDING_BOX", {"forceInput": True}),
                "sort": (SORT_OPTIONS, {"default": "as_given", "tooltip": "as_given keeps the input order; left_to_right orders by box centre-x."}),
                "start_index": ("INT", {"default": 1, "min": 0, "max": 100000}),
                "line_width": ("INT", {"default": 0, "min": 0, "max": 64, "tooltip": "0 = auto (0.3% of the short edge, min 2)."}),
                "font_scale": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 0.5, "step": 0.005, "tooltip": "Label height as a fraction of the short edge. 0 = auto (0.025, min 14 px)."}),
                "color": ("STRING", {"default": "#ff2020", "tooltip": "Box and label colour (hex or CSS name)."}),
                "show_score": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "BOUNDING_BOX", "STRING")
    RETURN_NAMES = ("image", "bboxes", "labels_json")
    FUNCTION = "draw"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Draws bounding boxes with legible number labels (optionally left to right) and returns the boxes in drawn order."

    def draw(self, image, bboxes, sort="as_given", start_index=1, line_width=0, font_scale=0.0, color="#ff2020", show_score=False):
        try:
            rgb = ImageColor.getrgb(color.strip())[:3]
        except ValueError as e:
            raise ValueError(f"Invalid color {color!r}: {e}") from e

        frames = _per_frame(bboxes, image.shape[0])
        if sort == "left_to_right":
            frames = [sort_left_to_right(frame) for frame in frames]

        out_images, labels = [], []
        for fi, (frame_img, boxes) in enumerate(zip(image, frames)):
            arr = np.clip(np.round(frame_img[..., :3].cpu().numpy() * 255.0), 0, 255).astype(np.uint8)
            img = Image.fromarray(arr)
            short = min(img.size)
            lw = line_width or max(2, round(short * AUTO_LINE_FRACTION))
            font_px = max(MIN_FONT_PX, round(short * (font_scale or AUTO_FONT_FRACTION)))
            _draw_frame(img, boxes, start_index, lw, font_px, rgb, show_score)
            out_images.append(torch.from_numpy(np.asarray(img).astype(np.float32) / 255.0))

            for n, b in enumerate(boxes):
                entry = {"frame": fi, "index": start_index + n,
                         **{k: round(float(b[k]), 1) for k in ("x", "y", "width", "height")}}
                if "score" in b:
                    entry["score"] = round(float(b["score"]), 4)
                labels.append(entry)

        return (torch.stack(out_images), frames, json.dumps(labels))


NODE_CLASS_MAPPINGS = {
    "DrawNumberedBBoxes": DrawNumberedBBoxes,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DrawNumberedBBoxes": "Draw Numbered BBoxes",
}
