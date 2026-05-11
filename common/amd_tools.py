"""
Save AMD Video - ComfyUI Custom Node

Direct copy of the SaveVideo node with the AMD GPU audio fix applied.

Fix: .float().numpy() -> .float().cpu().numpy() in video_types.py
"""

from __future__ import annotations

import os
import re
import torch
import folder_paths
from fractions import Fraction
from comfy_api.latest import ComfyExtension, io, ui, Input
from comfy.cli_args import args


def _apply_amd_gpu_patch():
    """Patch video_types.py: add .cpu() before .numpy() on audio waveform."""
    try:
        from comfy_api.latest._input_impl import video_types

        if hasattr(video_types, 'VideoFromComponents'):
            original_save_to = video_types.VideoFromComponents.save_to

            def patched_save_to(self, path, format, codec, metadata=None):
                components = getattr(self, '_VideoFromComponents__components', None)
                if components and components.audio is not None:
                    wf = components.audio.get('waveform')
                    if isinstance(wf, torch.Tensor) and wf.device.type != 'cpu':
                        components.audio['waveform'] = wf.cpu()
                return original_save_to(self, path, format, codec, metadata)

            video_types.VideoFromComponents.save_to = patched_save_to
            print("[Save AMD Video] Patched video_types for AMD GPU audio fix")
    except Exception as e:
        print(f"[Save AMD Video] Warning: patch not applied: {e}")


_apply_amd_gpu_patch()


class SaveAMDVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SaveAMDVideo",
            display_name="Save AMD Video",
            category="image/video",
            essentials_category="Basics",
            description="Saves the input video to your ComfyUI output directory. Includes AMD GPU audio fix.",
            inputs=[
                io.Video.Input("video", tooltip="The video to save."),
                io.String.Input("filename_prefix", default="video/ComfyUI", tooltip="The prefix for the file to save."),
                io.Combo.Input("format", options=io.Types.VideoContainer.as_input(), default="auto", tooltip="The format to save the video as."),
                io.Combo.Input("codec", options=io.Types.VideoCodec.as_input(), default="auto", tooltip="The codec to use for the video."),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, video: Input.Video, filename_prefix, format: str, codec) -> io.NodeOutput:
        width, height = video.get_dimensions()
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
            filename_prefix,
            folder_paths.get_output_directory(),
            width,
            height
        )
        saved_metadata = None
        if not args.disable_metadata:
            metadata = {}
            if cls.hidden.extra_pnginfo is not None:
                metadata.update(cls.hidden.extra_pnginfo)
            if cls.hidden.prompt is not None:
                metadata["prompt"] = cls.hidden.prompt
            if len(metadata) > 0:
                saved_metadata = metadata
        file = f"{filename}_{counter:05}_.{io.Types.VideoContainer.get_extension(format)}"
        video.save_to(
            os.path.join(full_output_folder, file),
            format=io.Types.VideoContainer(format),
            codec=codec,
            metadata=saved_metadata
        )

        return io.NodeOutput(ui=ui.PreviewVideo([ui.SavedResult(file, subfolder, io.FolderType.output)]))


NODE_CLASS_MAPPINGS = {
    "SaveAMDVideo": SaveAMDVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveAMDVideo": "Save AMD Video",
}
