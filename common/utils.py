"""
Image and Audio conversion utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Converting ComfyUI tensors to base64 encoded data URIs
- Converting base64 encoded data URIs back to tensors
- JSON serialization helpers for debug output
"""

import io
import base64
from typing import Optional, Union, Any

import torch
from PIL import Image
from torchvision import transforms
import soundfile as sf


def is_type(filename: str, extensions: tuple) -> bool:
    """
    Check if a filename has one of the given extensions.
    
    Args:
        filename: The filename or path to check
        extensions: Tuple of file extensions to match (e.g., (".png", ".jpg"))
        
    Returns:
        True if filename ends with any of the extensions, False otherwise
        
    Examples:
        >>> is_type("image.png", (".png", ".jpg"))
        True
        >>> is_type("image.gif", (".png", ".jpg"))
        False
        >>> is_type("", (".png", ".jpg"))
        False
    """
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in extensions)


def image_to_base64(image: Union[Image.Image, torch.Tensor]) -> str:
    """
    Convert a PIL Image or tensor to a base64 encoded data URI.
    
    Args:
        image: PIL Image or torch.Tensor (BxHxWxC format)
        
    Returns:
        Base64 encoded data URI string (data:image/png;base64,...)
    """
    if isinstance(image, torch.Tensor):
        # Handle different tensor formats
        if image.dim() == 4:  # BxCxHxW
            image = image.squeeze(0)
        if image.size(0) in [1, 3, 4]:  # CxHxW format
            image = image.permute(1, 2, 0)
        image = tensor_to_pil_image(image)
    
    buffer = io.BytesIO()
    if image.mode != "RGB":
        image = image.convert("RGB")
    image.save(buffer, format="PNG")
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def tensor_to_pil_image(tensor: torch.Tensor) -> Image.Image:
    """
    Convert a torch.Tensor to a PIL Image.
    
    Args:
        tensor: torch.Tensor in HxW or CxHxW format
        
    Returns:
        PIL Image
    """
    if tensor.dim() == 3 and tensor.size(0) in [1, 3, 4]:
        # CxHxW format, convert to HxWxC
        tensor = tensor.permute(1, 2, 0)
    
    to_pil = transforms.ToPILImage()
    return to_pil(tensor)


def audio_to_base64(
    audio: Union[tuple, dict], 
    format: str = "wav"
) -> str:
    """
    Convert audio data to a base64 encoded data URI.
    
    Args:
        audio: Either a tuple of (waveform, sample_rate) or a dict with 
               'waveform' and 'sample_rate' keys
        format: Audio format (wav, mp3, etc.)
        
    Returns:
        Base64 encoded data URI string (data:audio/wav;base64,...)
    """
    if isinstance(audio, dict):
        waveform = audio.get("waveform")
        sample_rate = audio.get("sample_rate")
    else:
        waveform, sample_rate = audio
    
    # Ensure waveform is 2D
    if isinstance(waveform, torch.Tensor):
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.dim() > 2:
            waveform = waveform.squeeze()
            if waveform.dim() > 2:
                raise ValueError("Waveform must be 1D or 2D")
        waveform_np = waveform.numpy().T
    else:
        waveform_np = waveform
        if waveform_np.ndim == 1:
            waveform_np = waveform_np.reshape(1, -1)
    
    buffer = io.BytesIO()
    sf.write(buffer, waveform_np, sample_rate, format=format)
    buffer.seek(0)
    audio_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:audio/{format};base64,{audio_str}"


def base64_to_tensor(
    base64_str: str, 
    mode: str = "RGB"
) -> Optional[torch.Tensor]:
    """
    Convert a base64 image string to a torch.Tensor.
    
    Args:
        base64_str: Base64 encoded image data URI
        mode: PIL image mode (RGB, RGBA, L, etc.)
        
    Returns:
        torch.Tensor in BxHxWxC format, or None if conversion fails
    """
    if not base64_str or not isinstance(base64_str, str):
        return None
    
    try:
        # Extract base64 content from data URL
        if "," in base64_str:
            base64_data = base64_str.split(",", 1)[1]
        else:
            base64_data = base64_str
        
        image_data = base64.b64decode(base64_data, validate=True)
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != mode:
            image = image.convert(mode)
        
        transform = transforms.ToTensor()
        tensor_image = transform(image)
        tensor_image = tensor_image.unsqueeze(0)  # Add batch dimension
        tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()  # HxWxC format
        
        return tensor_image
    except Exception as e:
        print(f"Error converting base64 to tensor: {e}")
        return None


def base64_audio_to_tensor(
    base64_str: str,
    format: str = "wav"
) -> Optional[dict]:
    """
    Convert a base64 audio string to audio data.
    
    Args:
        base64_str: Base64 encoded audio data URI
        format: Audio format (wav, mp3, etc.)
        
    Returns:
        Dict with 'waveform' (tensor) and 'sample_rate' (int), or None if fails
    """
    if not base64_str or not isinstance(base64_str, str):
        return None
    
    try:
        # Extract base64 content from data URL
        if "," in base64_str:
            base64_data = base64_str.split(",", 1)[1]
        else:
            base64_data = base64_str
        
        audio_data = base64.b64decode(base64_data, validate=True)
        audio_buffer = io.BytesIO(audio_data)
        
        waveform, sample_rate = sf.load(audio_buffer, format=format)
        
        return {
            "waveform": torch.from_numpy(waveform).unsqueeze(0),
            "sample_rate": sample_rate
        }
    except Exception as e:
        print(f"Error converting base64 to audio tensor: {e}")
        return None


def convert_to_json_serializable(obj: Any) -> Any:
    """
    Convert objects to JSON serializable format.
    
    Useful for debug output and logging.
    
    Args:
        obj: Any object to convert
        
    Returns:
        JSON serializable version of the object
    """
    if isinstance(obj, torch.Tensor):
        # Return tensor shape info instead of full data for debugging
        return f"<Tensor shape={list(obj.shape)}, dtype={obj.dtype}>"
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj


def format_value_for_log(value: Any) -> Any:
    """
    Format a value for logging, truncating large data like base64 strings.
    
    Args:
        value: The value to format
        
    Returns:
        Formatted value safe for logging
    """
    if isinstance(value, torch.Tensor):
        return f"<Tensor {list(value.shape)} {value.dtype}>"
    elif isinstance(value, list):
        return [format_value_for_log(item) for item in value]
    elif isinstance(value, str):
        # Truncate base64 strings for readability
        if value.startswith("data:image") or value.startswith("data:audio"):
            comma_idx = value.find(",")
            if comma_idx != -1:
                return value[:comma_idx + 1] + "..."
            return value[:20] + "..."
        elif len(value) > 100:
            return value[:100] + "..."
    return value


def pil_image_to_tensor(image: Image.Image) -> torch.Tensor:
    """
    Convert a PIL Image to a torch.Tensor.
    
    Args:
        image: PIL Image
        
    Returns:
        torch.Tensor in BxHxWxC format
    """
    transform = transforms.ToTensor()
    tensor_image = transform(image)
    tensor_image = tensor_image.unsqueeze(0)  # Add batch dimension
    tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
    return tensor_image
