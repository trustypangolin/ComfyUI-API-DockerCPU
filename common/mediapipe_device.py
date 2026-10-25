"""
MediaPipe face landmarker loader with a device choice.

Native LoadMediaPipeFaceLandmarker always loads onto text_encoder_device()
(the GPU when one is present). This loader reuses the native model wrapper
and outputs the same FACE_DETECTION_MODEL type, so the native
MediaPipeFaceLandmarker / MediaPipeFaceMask nodes work downstream, but can
pin the model to the CPU.
"""

import torch

import comfy.model_management
import comfy.model_patcher
import comfy.utils
import folder_paths
from comfy_extras.nodes_mediapipe import FaceLandmarkerModel

DEVICE_OPTIONS = ["cpu", "default"]


class CPUFaceLandmarkerModel(FaceLandmarkerModel):
    """Native wrapper with its per-variant ModelPatchers rebuilt to load on CPU."""

    def __init__(self, state_dict):
        super().__init__(state_dict)
        cpu = torch.device("cpu")
        self.load_device = cpu
        for variant, fl in self.models.items():
            fl.to(cpu)
            self.patchers[variant] = comfy.model_patcher.CoreModelPatcher(
                fl, load_device=cpu, offload_device=cpu,
                size=comfy.model_management.module_size(fl),
            )


class LoadMediaPipeFaceLandmarkerDevice:
    """
    Load MediaPipe Face Landmarker weights on a chosen device.

    device:
        cpu:     Always run on CPU (small model; frees the GPU)
        default: Same as the native loader (text_encoder_device)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_name": (folder_paths.get_filename_list("detection"), {"tooltip": "Face detection model from models/detection/."}),
                "device": (DEVICE_OPTIONS, {"default": "cpu"}),
            },
        }

    RETURN_TYPES = ("FACE_DETECTION_MODEL",)
    RETURN_NAMES = ("face_detection_model",)
    FUNCTION = "load"
    CATEGORY = "🎨 DockerCPU API/Face"
    DESCRIPTION = "Loads the MediaPipe face landmarker like the native loader, but on a chosen device (CPU by default)."

    def load(self, model_name, device="cpu"):
        sd = comfy.utils.load_torch_file(folder_paths.get_full_path_or_raise("detection", model_name), safe_load=True)
        if device == "cpu":
            return (CPUFaceLandmarkerModel(sd),)
        return (FaceLandmarkerModel(sd),)


NODE_CLASS_MAPPINGS = {
    "LoadMediaPipeFaceLandmarkerDevice": LoadMediaPipeFaceLandmarkerDevice,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadMediaPipeFaceLandmarkerDevice": "Load Face Detection Model (MediaPipe, device)",
}
