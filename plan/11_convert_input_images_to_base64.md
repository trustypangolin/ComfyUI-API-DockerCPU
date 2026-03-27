# Plan: Extract `convert_input_images_to_base64()` Function

## Function Overview
**Function Name**: `convert_input_images_to_base64()`
**Current Location**: 
- `API/FalAi/node.py` (lines 70-101)
- `API/Replicate/node.py` (lines 98-129)

**Target Location**: `common/input_handlers.py`

## Current Implementations (~90% Similar)

The implementations are nearly identical, with minor differences in how they call helper methods:

### FalAi Version
```python
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
```

### Replicate Version
(Same logic, just calls `self._image_to_base64()` and `self._audio_to_base64()`)

## Why Extract
- **Duplication Level**: ~90% similar (minor differences in helper method calls)
- **Risk Level**: Medium (need to handle helper method dependencies)
- **Impact**: High (used in all model inputs)
- **Lines Saved**: ~90 lines (45 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/input_handlers.py`
Add the function with helper function parameters:

```python
def convert_input_images_to_base64(
    kwargs: Dict[str, Any],
    input_types: Dict[str, Any],
    image_to_base64_func: callable,
    audio_to_base64_func: callable
) -> None:
    """
    Convert image tensors to base64 data URIs.
    
    Modifies kwargs in-place.
    
    Args:
        kwargs: Dictionary of input parameters
        input_types: Dictionary of input type definitions (from INPUT_TYPES())
        image_to_base64_func: Function to convert image tensor to base64
        audio_to_base64_func: Function to convert audio tensor to base64
        
    Examples:
        >>> kwargs = {"image": torch.Tensor(...)}
        >>> input_types = {"required": {"image": ("IMAGE",)}}
        >>> convert_input_images_to_base64(kwargs, input_types, image_to_base64, audio_to_base64)
        >>> kwargs["image"]
        'data:image/png;base64,...'
    """
    for key, value in kwargs.items():
        if value is None:
            continue
        
        # Check for tensor inputs
        if isinstance(value, torch.Tensor):
            kwargs[key] = image_to_base64_func(value)
            continue
        
        # Check for list with tensors
        if isinstance(value, list) and any(isinstance(item, torch.Tensor) for item in value):
            kwargs[key] = [image_to_base64_func(item) for item in value]
            continue
        
        # Check input type mapping
        input_type = (
            input_types.get("required", {}).get(key, (None,))[0]
            or input_types.get("optional", {}).get(key, (None,))[0]
        )
        
        if input_type == "IMAGE":
            if isinstance(value, list):
                kwargs[key] = [image_to_base64_func(item) for item in value]
            else:
                kwargs[key] = image_to_base64_func(value)
        elif input_type == "AUDIO":
            if isinstance(value, list):
                kwargs[key] = [audio_to_base64_func(item) for item in value]
            else:
                kwargs[key] = audio_to_base64_func(value)
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `convert_input_images_to_base64()` method definition (lines 70-101)
- Add import: `from common.input_handlers import convert_input_images_to_base64`
- Update method to call the common function:
  ```python
  def convert_input_images_to_base64(self, kwargs):
      """Convert image tensors to base64 data URIs."""
      convert_input_images_to_base64(
          kwargs,
          self.INPUT_TYPES(),
          self._image_to_base64,
          self._audio_to_base64
      )
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `convert_input_images_to_base64()` method definition (lines 98-129)
- Add import: `from common.input_handlers import convert_input_images_to_base64`
- Update method to call the common function:
  ```python
  def convert_input_images_to_base64(self, kwargs):
      """Convert image tensors to base64 data URIs."""
      convert_input_images_to_base64(
          kwargs,
          self.INPUT_TYPES(),
          self._image_to_base64,
          self._audio_to_base64
      )
  ```

## Testing Checklist

- [ ] Verify function converts single image tensor to base64
- [ ] Verify function converts list of image tensors to base64
- [ ] Verify function converts single audio tensor to base64
- [ ] Verify function converts list of audio tensors to base64
- [ ] Verify function handles None values correctly
- [ ] Verify function handles non-tensor values correctly
- [ ] Verify function modifies kwargs in-place
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`
- Depends on `_image_to_base64()` and `_audio_to_base64()` helper functions

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
