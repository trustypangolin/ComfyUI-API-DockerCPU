"""
Save AMD Video - ComfyUI Custom Node

Direct copy of the SaveVideo node with the AMD GPU audio fix applied.

Fix: .float().numpy() -> .float().cpu().numpy() in video_types.py
"""

import os
import torch
import folder_paths
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


class SaveAMDVideo:
    @classmethod
    def INPUT_TYPES(cls):
        from comfy_api.latest import Types
        return {
            "required": {
                "video": ("VIDEO", {"tooltip": "The video to save."}),
                "filename_prefix": ("STRING", {"default": "video/ComfyUI", "tooltip": "The prefix for the file to save."}),
                "format": (Types.VideoContainer.as_input(), {"default": "auto", "tooltip": "The format to save the video as."}),
                "codec": (Types.VideoCodec.as_input(), {"default": "auto", "tooltip": "The codec to use for the video."}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True

    CATEGORY = "image/video"
    DESCRIPTION = "Saves the input video to your ComfyUI output directory. Includes AMD GPU audio fix."

    def save_video(self, video, filename_prefix, format, codec, prompt=None, extra_pnginfo=None):
        from comfy_api.latest import Types

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
            if extra_pnginfo is not None:
                metadata.update(extra_pnginfo)
            if prompt is not None:
                metadata["prompt"] = prompt
            if len(metadata) > 0:
                saved_metadata = metadata
        file = f"{filename}_{counter:05}_.{Types.VideoContainer.get_extension(format)}"
        video.save_to(
            os.path.join(full_output_folder, file),
            format=Types.VideoContainer(format),
            codec=codec,
            metadata=saved_metadata
        )

        return {
            "ui": {
                "images": [
                    {
                        "filename": file,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ],
                "animated": (True,),
            },
        }


NODE_CLASS_MAPPINGS = {
    "SaveAMDVideo": SaveAMDVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveAMDVideo": "Save AMD Video",
}
