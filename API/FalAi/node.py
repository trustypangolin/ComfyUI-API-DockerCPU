"""
FalAi API Node for ComfyUI-API-DockerCPU

Creates dynamic ComfyUI nodes from Fal.ai model schemas.
Supports dry_run mode for testing without API calls.
"""

import os
import json
import time
from io import BytesIO
from typing import Dict, Any, Tuple

import torch
import numpy as np
from torchvision import transforms
import torchaudio
from PIL import Image
from PIL import Image

try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    FAL_AVAILABLE = False
    fal_client = None

from .schema_to_node import (
    schema_to_comfyui_input_types,
    get_return_type,
    name_and_version,
    inputs_that_need_arrays,
)
from common.output_handlers import handle_image_output as _handle_image_output
from common.output_handlers import handle_audio_output as _handle_audio_output
from common.input_handlers import handle_array_inputs as _handle_array_inputs
from common.input_handlers import handle_array_inputs as _handle_array_inputs
from common.output_handlers import handle_image_output as _handle_image_output
from common.output_handlers import handle_audio_output as _handle_audio_output
from common.output_handlers import handle_image_output as _handle_image_output
from common.output_handlers import handle_audio_output as _handle_audio_output


def create_comfyui_node(schema: Dict) -> Tuple[str, type]:
    """
    Create a ComfyUI node class from a Fal.ai schema.
    
    Args:
        schema: Fal.ai OpenAPI schema
        
    Returns:
        Tuple of (node_name, node_class)
    """
    fal_model, node_name = name_and_version(schema)
    return_type = get_return_type(schema)

    class FalAiToComfyUI:
        """Dynamic ComfyUI node for Fal.ai models."""

        @classmethod
        def IS_CHANGED(cls, **kwargs):
            return time.time() if kwargs.get("force_rerun") else ""

        @classmethod
        def INPUT_TYPES(cls):
            return schema_to_comfyui_input_types(schema)

        RETURN_TYPES = (
            tuple(return_type.values())
            if isinstance(return_type, dict)
            else (return_type,)
        ) + ("STRING",)
        RETURN_NAMES = (
            tuple(return_type.keys())
            if isinstance(return_type, dict)
            else ("output",)
        ) + ("API_JSON",)
        FUNCTION = "run_model"
        CATEGORY = "🎨 DockerCPU API/🎨 FalAi"

        def convert_input_images_to_base64(self, kwargs):
            """Convert image tensors to base64 data URIs."""
            for key, value in kwargs.items():
                if value is None:
                    continue
                
                # Check for tensor inputs
                if isinstance(value, torch.Tensor):
                    kwargs[key] = self._image_to_base64(value)
                    continue
                
                # Check for list with tensors
                if isinstance(value, list) and any(isinstance(item, torch.Tensor) for item in value):
                    kwargs[key] = [self._image_to_base64(item) for item in value]
                    continue
                
                # Check input type mapping
                input_type = (
                    self.INPUT_TYPES().get("required", {}).get(key, (None,))[0]
                    or self.INPUT_TYPES().get("optional", {}).get(key, (None,))[0]
                )
                
                if input_type == "IMAGE":
                    if isinstance(value, list):
                        kwargs[key] = [self._image_to_base64(item) for item in value]
                    else:
                        kwargs[key] = self._image_to_base64(value)
                elif input_type == "AUDIO":
                    if isinstance(value, list):
                        kwargs[key] = [self._audio_to_base64(item) for item in value]
                    else:
                        kwargs[key] = self._audio_to_base64(value)

        def _image_to_base64(self, image):
            """Convert image tensor to base64 data URI."""
            import base64
            from PIL import Image
            
            if isinstance(image, torch.Tensor):
                # Handle 4D tensor (batch, height, width, channels) -> assume batch size 1
                if image.dim() == 4:
                    image = image.squeeze(0)
                # Now expect 3D tensor (height, width, channels)
                if image.dim() != 3:
                    raise ValueError(f"Expected 3D or 4D image tensor, got {image.dim()}D")
                
                # Convert to numpy array and normalize
                image = image.cpu().numpy()
                if image.max() <= 1.0:
                    image = (image * 255).clip(0, 255).astype(np.uint8)
                else:
                    image = image.clip(0, 255).astype(np.uint8)
                
                # Handle grayscale
                if image.shape[2] == 1:
                    image = image[:, :, 0]
                pil_image = Image.fromarray(image)
                
                # Ensure RGB format
                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
            else:
                pil_image = image

            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"

        def _audio_to_base64(self, audio):
            """Convert audio tensor to base64 data URI."""
            import base64
            import soundfile as sf
            
            if isinstance(audio, dict):
                waveform = audio.get("waveform")
                sample_rate = audio.get("sample_rate")
            else:
                waveform, sample_rate = audio

            if isinstance(waveform, torch.Tensor):
                if waveform.dim() == 1:
                    waveform = waveform.unsqueeze(0)
                waveform_np = waveform.numpy().T
            else:
                waveform_np = waveform

            buffer = BytesIO()
            sf.write(buffer, waveform_np, sample_rate, format="wav")
            buffer.seek(0)
            audio_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:audio/wav;base64,{audio_str}"

        def _base64_to_tensor(self, base64_str):
            """Convert base64 image to tensor."""
            import base64
            if not base64_str or not isinstance(base64_str, str):
                return None
            try:
                if "," in base64_str:
                    base64_data = base64_str.split(",", 1)[1]
                else:
                    base64_data = base64_str
                image_data = base64.b64decode(base64_data)
                image = Image.open(BytesIO(image_data))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                transform = transforms.ToTensor()
                tensor_image = transform(image)
                tensor_image = tensor_image.unsqueeze(0)
                tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                return tensor_image
            except Exception as e:
                print(f"Error converting base64 to tensor: {e}")
                return None

        def handle_array_inputs(self, kwargs):
            """Convert string array inputs to proper arrays."""
            array_inputs = inputs_that_need_arrays(schema)
            _handle_array_inputs(kwargs, array_inputs)

        def remove_falsey_optional_inputs(self, kwargs):
            """Remove empty/None optional inputs."""
            optional_inputs = self.INPUT_TYPES().get("optional", {})
            for key in list(kwargs.keys()):
                if key in optional_inputs:
                    if isinstance(kwargs[key], torch.Tensor):
                        continue
                    elif not kwargs[key]:
                        del kwargs[key]

        def handle_image_output(self, output):
            """Process image output from API."""
            return _handle_image_output(output)

        def handle_audio_output(self, output):
            """Process audio output from API."""
            return _handle_audio_output(output)
            try:
                if base64_str.startswith("data:"):
                    base64_data = base64_str.split(",", 1)[1]
                else:
                    base64_data = base64_str

                image_data = base64.b64decode(base64_data)
                image = Image.open(BytesIO(image_data))
                if image.mode != "RGB":
                    image = image.convert("RGB")

                transform = transforms.ToTensor()
                tensor_image = transform(image)
                tensor_image = tensor_image.unsqueeze(0)
                tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                return tensor_image
            except Exception as e:
                print(f"Error converting base64 to tensor: {e}")
                return None

        def run_model(self, **kwargs):
            """Execute the model or return dry run data."""
            from PIL import Image
            
            # Extract dry_run flag
            dry_run_mode = kwargs.pop("dry_run", False)

            # Process inputs
            self.handle_array_inputs(kwargs)
            self.remove_falsey_optional_inputs(kwargs)
            self.convert_input_images_to_base64(kwargs)

            # Log inputs
            self._log_input(kwargs)

            # Remove special parameters from API call
            kwargs_for_api = {
                k: v for k, v in kwargs.items()
                if k not in ["force_rerun", "dry_run"]
            }

            # Prepare JSON output
            input_json = json.dumps(kwargs_for_api, indent=2, default=str)

            # Dry run mode: skip API call
            if dry_run_mode:
                return self._dry_run_output(kwargs_for_api, input_json, return_type)

            # Execute API call
            if not FAL_AVAILABLE:
                raise RuntimeError("Fal.ai client not available. Install fal-client package and set FAL_KEY.")
            
            output = fal_client.subscribe(fal_model, kwargs_for_api)

            # Process outputs
            processed_outputs = self._process_output(output, return_type)
            processed_outputs.append(input_json)
            return tuple(processed_outputs)

        def _log_input(self, kwargs):
            """Log input parameters."""
            def format_value(v):
                if isinstance(v, list):
                    return [format_value(item) for item in v]
                elif isinstance(v, str) and (v.startswith("data:image") or v.startswith("data:audio")):
                    comma_idx = v.find(",")
                    if comma_idx != -1:
                        return v[:comma_idx + 1] + "..."
                    return v[:20] + "..."
                return v

            truncated_kwargs = {k: format_value(v) for k, v in kwargs.items()}
            print(f"Running {fal_model} with {truncated_kwargs}")

        def _dry_run_output(self, kwargs, input_json, return_type):
            """Generate dry run output without API call."""
            print(f"DRY RUN MODE: Skipping API call, returning input data")
            print(f"Input JSON: {input_json}")

            # Find first image to return
            debug_tensor = None
            for key, value in kwargs.items():
                if isinstance(value, str) and value.startswith("data:image"):
                    debug_tensor = self._base64_to_tensor(value)
                    break
                elif key in ["image", "images", "input_image", "image_url", "image_urls"]:
                    if isinstance(value, list) and value:
                        debug_tensor = self._base64_to_tensor(value[0])
                    elif isinstance(value, str) and value:
                        debug_tensor = self._base64_to_tensor(value)
                    break

            processed_outputs = []
            if isinstance(return_type, dict):
                for prop_name, prop_type in return_type.items():
                    if prop_type == "IMAGE":
                        processed_outputs.append(debug_tensor)
                    elif prop_type == "AUDIO":
                        processed_outputs.append(None)
                    elif prop_type == "VIDEO_URI":
                        processed_outputs.append(None)
                    else:
                        processed_outputs.append("")
            else:
                if return_type == "IMAGE":
                    processed_outputs.append(debug_tensor)
                elif return_type == "AUDIO":
                    processed_outputs.append(None)
                else:
                    processed_outputs.append("")

            processed_outputs.append(input_json)
            return tuple(processed_outputs)

        def _process_output(self, output, return_type):
            """Process API output into ComfyUI format."""
            processed_outputs = []
            
            if isinstance(return_type, dict):
                for prop_name, prop_type in return_type.items():
                    if prop_type == "IMAGE":
                        processed_outputs.append(self.handle_image_output(output.get(prop_name)))
                    elif prop_type == "AUDIO":
                        processed_outputs.append(self.handle_audio_output(output.get(prop_name)))
                    elif prop_type == "VIDEO_URI":
                        processed_outputs.append(output.get(prop_name))
                    elif prop_type == "STRING":
                        val = output.get(prop_name, "")
                        processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else str(val))
                    else:
                        processed_outputs.append(output.get(prop_name, ""))
            else:
                if return_type == "IMAGE":
                    processed_outputs.append(self.handle_image_output(output))
                elif return_type == "AUDIO":
                    processed_outputs.append(self.handle_audio_output(output))
                else:
                    val = output if isinstance(output, (list, tuple)) else str(output)
                    processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else val)

            return processed_outputs

    return node_name, FalAiToComfyUI


def create_nodes(schemas_dir: str = None) -> Dict[str, type]:
    """
    Create all ComfyUI nodes from schema files.
    
    Args:
        schemas_dir: Directory containing JSON schema files.
                    If None, uses the default schemas directory.
    
    Returns:
        Dictionary mapping node names to node classes
    """
    if schemas_dir is None:
        # Get the package directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Use local schemas folder: package_dir/schemas/FalAi/
        schemas_dir = os.path.join(package_dir, "schemas", "FalAi")
    
    nodes = {}
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: Schemas directory not found: {schemas_dir}")
        return nodes
    
    for schema_file in os.listdir(schemas_dir):
        if schema_file.endswith(".json"):
            try:
                with open(os.path.join(schemas_dir, schema_file), "r", encoding="utf-8") as f:
                    schema = json.load(f)
                node_name, node_class = create_comfyui_node(schema)
                nodes[node_name] = node_class
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")
    
    return nodes
