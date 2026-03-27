"""
Output processing utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Processing image outputs from APIs
- Processing audio outputs from APIs
- Converting API responses to ComfyUI format
"""

from io import BytesIO
from typing import Optional, Union, List, Dict, Any

import torch
from torchvision import transforms
import torchaudio
from PIL import Image


def handle_image_output(output) -> Optional[torch.Tensor]:
    """
    Process image output from API.
    
    Converts file-like objects or lists of file-like objects to tensors.
    
    Args:
        output: Single file-like object or list of file-like objects
                containing image data
                
    Returns:
        torch.Tensor in BxHxWxC format, or None if output is empty
        
    Examples:
        >>> # Single image
        >>> tensor = handle_image_output(file_obj)
        >>> tensor.shape
        torch.Size([1, 512, 512, 3])
        
        >>> # Multiple images
        >>> tensor = handle_image_output([file_obj1, file_obj2])
        >>> tensor.shape
        torch.Size([2, 512, 512, 3])
    """
    if output is None:
        return None

    output_list = output if isinstance(output, list) else [output]
    if not output_list:
        return None

    output_tensors = []
    transform = transforms.ToTensor()
    
    for file_obj in output_list:
        image_data = file_obj.read()
        image = Image.open(BytesIO(image_data))
        if image.mode != "RGB":
            image = image.convert("RGB")

        tensor_image = transform(image)
        tensor_image = tensor_image.unsqueeze(0)
        tensor_image = tensor_image.permute(0, 2, 3, 1).cpu().float()
        output_tensors.append(tensor_image)

    return torch.cat(output_tensors, dim=0) if len(output_tensors) > 1 else output_tensors[0]


def handle_audio_output(output) -> Optional[Union[Dict, List[Dict]]]:
    """
    Process audio output from API.
    
    Converts file-like objects or lists of file-like objects to audio data.
    
    Args:
        output: Single file-like object or list of file-like objects
                containing audio data
                
    Returns:
        Dict with 'waveform' and 'sample_rate', list of such dicts, or None
    """
    if output is None:
        return None

    output_list = output if isinstance(output, list) else [output]
    audio_data = []
    
    for audio_file in output_list:
        if audio_file:
            audio_content = BytesIO(audio_file.read())
            waveform, sample_rate = torchaudio.load(audio_content)
            audio_data.append({
                "waveform": waveform.unsqueeze(0),
                "sample_rate": sample_rate
            })

    if len(audio_data) == 1:
        return audio_data[0]
    elif len(audio_data) > 0:
        return audio_data
    return None
