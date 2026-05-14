"""
ZIP Utilities for ComfyUI-API-DockerCPU

Provides nodes for loading and extracting ZIP archives:
- LoadZIP: Load PNG images from a ZIP file URL/path
- LoadPrediction: Load output from a Replicate prediction by ID
"""

import os
import zipfile
import urllib.request
from io import BytesIO
from typing import Optional, Tuple

import torch
from torchvision import transforms
from PIL import Image

try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    replicate = None


class LoadZIP:
    """
    Load PNG images from a ZIP archive.
    
    Accepts a URL or file path to a ZIP file and extracts PNG images.
    Returns the images as a batch tensor.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "zip_path": ("STRING", {
                    "default": "",
                    "tooltip": "URL or file path to the ZIP archive"
                }),
            },
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "zip_info")
    FUNCTION = "load_zip"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    
    def load_zip(self, zip_path: str) -> Tuple[torch.Tensor, str]:
        """
        Load PNG images from a ZIP archive.
        
        Args:
            zip_path: URL or file path to the ZIP file
            
        Returns:
            Tuple of (image_tensor, info_string)
        """
        transform = transforms.ToTensor()
        output_tensors = []
        
        # Get ZIP content
        if zip_path.startswith("http://") or zip_path.startswith("https://"):
            # Fetch from URL
            with urllib.request.urlopen(zip_path) as response:
                zip_data = response.read()
        else:
            # Load from file path
            with open(zip_path, "rb") as f:
                zip_data = f.read()
        
        # Extract PNG files
        with zipfile.ZipFile(BytesIO(zip_data), 'r') as zf:
            png_files = sorted([f for f in zf.namelist() if f.lower().endswith('.png')])
            
            for png_file in png_files:
                with zf.open(png_file) as img_file:
                    image = Image.open(img_file)
                    if image.mode != "RGB":
                        image = image.convert("RGB")
                    tensor_image = transform(image)
                    tensor_image = tensor_image.unsqueeze(0)
                    tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                    output_tensors.append(tensor_image)
        
        if not output_tensors:
            return None, "No PNG files found in ZIP"
        
        # Combine into batch
        result = torch.cat(output_tensors, dim=0) if len(output_tensors) > 1 else output_tensors[0]
        info = f"Loaded {len(output_tensors)} images from ZIP"
        
        return result, info


class LoadPrediction:
    """
    Load output from a Replicate prediction by ID.
    
    Given a prediction ID, fetch the prediction and process its output.
    Useful for re-running or downloading outputs from previous predictions.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prediction_id": ("STRING", {
                    "default": "",
                    "tooltip": "Replicate prediction ID (e.g., 'abc123')"
                }),
            },
            "optional": {
                "model_version": ("STRING", {
                    "default": "",
                    "tooltip": "Model version for the prediction (owner/model:version)"
                }),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "prediction_info")
    FUNCTION = "load_prediction"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    
    def _get_replicate_client(self):
        """Get or create Replicate client."""
        if not REPLICATE_AVAILABLE:
            raise RuntimeError("replicate package not installed")
        
        api_token = os.environ.get("REPLICATE_API_TOKEN")
        if not api_token:
            raise RuntimeError("REPLICATE_API_TOKEN not set")
        
        return replicate.Client(api_token=api_token)
    
    def _extract_images_from_output(self, output) -> Tuple[torch.Tensor, str]:
        """Extract images from prediction output."""
        transform = transforms.ToTensor()
        output_tensors = []
        
        if output is None:
            return None, "No output from prediction"
        
        # Handle list of outputs
        outputs = output if isinstance(output, list) else [output]
        
        for file_obj in outputs:
            # Get file content (handles FileOutput objects)
            if hasattr(file_obj, 'read'):
                try:
                    image_data = file_obj.read()
                except Exception:
                    continue
            elif isinstance(file_obj, str):
                # URL - fetch content
                with urllib.request.urlopen(file_obj) as response:
                    image_data = response.read()
            else:
                continue
            
            # Check for ZIP archive
            if zipfile.is_zipfile(BytesIO(image_data)):
                with zipfile.ZipFile(BytesIO(image_data), 'r') as zf:
                    png_files = sorted([f for f in zf.namelist() if f.lower().endswith('.png')])
                    for png_file in png_files:
                        with zf.open(png_file) as img_file:
                            image = Image.open(img_file)
                            if image.mode != "RGB":
                                image = image.convert("RGB")
                            tensor_image = transform(image)
                            tensor_image = tensor_image.unsqueeze(0)
                            tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                            output_tensors.append(tensor_image)
            else:
                # Single image
                image = Image.open(BytesIO(image_data))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                tensor_image = transform(image)
                tensor_image = tensor_image.unsqueeze(0)
                tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
                output_tensors.append(tensor_image)
        
        if not output_tensors:
            return None, "No images found in prediction output"
        
        result = torch.cat(output_tensors, dim=0) if len(output_tensors) > 1 else output_tensors[0]
        return result, f"Extracted {len(output_tensors)} images"
    
    def load_prediction(self, prediction_id: str, model_version: str = "") -> Tuple[torch.Tensor, str]:
        """
        Load output from a Replicate prediction by ID.
        
        Args:
            prediction_id: The prediction ID
            model_version: Optional model version identifier
            
        Returns:
            Tuple of (image_tensor, info_string)
        """
        client = self._get_replicate_client()
        
        try:
            if model_version:
                prediction = client.predictions.get(model_version, prediction_id)
            else:
                prediction = client.predictions.get(prediction_id)
            
            if prediction.status != "succeeded":
                return None, f"Prediction status: {prediction.status}"
            
            images, info = self._extract_images_from_output(prediction.output)
            return images, f"Prediction {prediction_id}: {info}"
            
        except Exception as e:
            return None, f"Error loading prediction: {str(e)}"


NODE_CLASS_MAPPINGS = {
    "LoadZIP": LoadZIP,
    "LoadPrediction": LoadPrediction,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoadZIP": "Load ZIP Archive",
    "LoadPrediction": "Load Replicate Prediction",
}