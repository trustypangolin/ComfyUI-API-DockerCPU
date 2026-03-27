# Plan: Extract `handle_image_output()` Function

## Function Overview
**Function Name**: `handle_image_output()`
**Current Location**: 
- `API/FalAi/node.py` (lines 172-195)
- `API/Replicate/node.py` (lines 232-255)

**Target Location**: `common/output_handlers.py` (NEW FILE)

## Current Implementation (100% Identical)

```python
def handle_image_output(self, output):
    """Process image output from API."""
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
```

## Why Extract
- **Duplication Level**: 100% identical in FalAi & Replicate
- **Risk Level**: Low
- **Impact**: High (used in all image model outputs)
- **Lines Saved**: ~70 lines (35 lines × 2 files)

## Implementation Steps

### Step 1: Create `common/output_handlers.py`
Create new file with the following content:

```python
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
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `handle_image_output()` method definition (lines 172-195)
- Add import: `from common.output_handlers import handle_image_output`
- Update method to call the common function:
  ```python
  def handle_image_output(self, output):
      """Process image output from API."""
      return handle_image_output(output)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `handle_image_output()` method definition (lines 232-255)
- Add import: `from common.output_handlers import handle_image_output`
- Update method to call the common function:
  ```python
  def handle_image_output(self, output):
      """Process image output from API."""
      return handle_image_output(output)
  ```

## Testing Checklist

- [x] Verify function handles None output correctly
- [x] Verify function handles single image file object
- [x] Verify function handles list of image file objects
- [x] Verify function converts RGBA to RGB
- [x] Verify function returns correct tensor shape (BxHxWxC)
- [x] Verify function concatenates multiple images correctly
- [x] Test with FalAi API
- [x] Test with Replicate API
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `torchvision`, `PIL`, `BytesIO`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
