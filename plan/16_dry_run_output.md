# Plan: Extract `_dry_run_output()` Function

## Function Overview
**Function Name**: `_dry_run_output()`
**Current Location**: 
- `API/FalAi/node.py` (lines 301-339)
- `API/Replicate/node.py` (lines 360-396)

**Target Location**: `common/dry_run.py` (NEW FILE)

## Current Implementations (~80% Similar)

The implementations are similar but have differences in how they find images and handle return types:

### FalAi Version
```python
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
```

### Replicate Version
```python
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
        elif key in ["image", "images", "input_image", "input_images", "media"]:
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
```

## Why Extract
- **Duplication Level**: ~80% similar (minor differences in image key names)
- **Risk Level**: Medium (need to handle different image key patterns)
- **Impact**: Medium (used in dry run mode)
- **Lines Saved**: ~80 lines (40 lines × 2 files)

## Implementation Steps

### Step 1: Create `common/dry_run.py`
Create new file with the following content:

```python
"""
Dry run utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Generating dry run output without API calls
- Finding debug images in input parameters
- Creating placeholder outputs for testing
"""

from typing import Dict, Any, List, Optional, Union

import torch


def find_debug_image(kwargs: Dict[str, Any], base64_to_tensor_func: callable) -> Optional[torch.Tensor]:
    """
    Find the first image in kwargs for dry run output.
    
    Args:
        kwargs: Dictionary of input parameters
        base64_to_tensor_func: Function to convert base64 to tensor
        
    Returns:
        First image tensor found, or None
    """
    # Check for base64 data URIs
    for key, value in kwargs.items():
        if isinstance(value, str) and value.startswith("data:image"):
            return base64_to_tensor_func(value)
    
    # Check for common image field names
    image_keys = ["image", "images", "input_image", "input_images", "image_url", "image_urls", "media"]
    for key in image_keys:
        if key in kwargs:
            value = kwargs[key]
            if isinstance(value, list) and value:
                return base64_to_tensor_func(value[0])
            elif isinstance(value, str) and value:
                return base64_to_tensor_func(value)
    
    return None


def generate_dry_run_output(
    kwargs: Dict[str, Any],
    input_json: str,
    return_type: Union[Dict[str, str], str],
    base64_to_tensor_func: callable
) -> tuple:
    """
    Generate dry run output without API call.
    
    Args:
        kwargs: Dictionary of input parameters
        input_json: JSON string of input parameters
        return_type: Return type specification (dict or string)
        base64_to_tensor_func: Function to convert base64 to tensor
        
    Returns:
        Tuple of output values matching the return type
        
    Examples:
        >>> kwargs = {"image": "data:image/png;base64,..."}
        >>> return_type = {"image": "IMAGE", "text": "STRING"}
        >>> outputs = generate_dry_run_output(kwargs, "{}", return_type, base64_to_tensor)
        >>> len(outputs)
        3
    """
    print(f"DRY RUN MODE: Skipping API call, returning input data")
    print(f"Input JSON: {input_json}")

    # Find first image to return
    debug_tensor = find_debug_image(kwargs, base64_to_tensor_func)

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
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_dry_run_output()` method definition (lines 301-339)
- Add import: `from common.dry_run import generate_dry_run_output`
- Update method to call the common function:
  ```python
  def _dry_run_output(self, kwargs, input_json, return_type):
      """Generate dry run output without API call."""
      return generate_dry_run_output(kwargs, input_json, return_type, self._base64_to_tensor)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_dry_run_output()` method definition (lines 360-396)
- Add import: `from common.dry_run import generate_dry_run_output`
- Update method to call the common function:
  ```python
  def _dry_run_output(self, kwargs, input_json, return_type):
      """Generate dry run output without API call."""
      return generate_dry_run_output(kwargs, input_json, return_type, self._base64_to_tensor)
  ```

## Testing Checklist

- [ ] Verify function finds base64 image data URIs
- [ ] Verify function finds images in common field names
- [ ] Verify function handles list of images
- [ ] Verify function handles single image
- [ ] Verify function generates correct outputs for dict return type
- [ ] Verify function generates correct outputs for string return type
- [ ] Verify function includes input_json in output
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`
- Depends on `base64_to_tensor()` function

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
