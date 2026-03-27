# Plan: Enhance `base64_to_tensor()` Function

## Function Overview
**Function Name**: `base64_to_tensor()` and `_base64_to_tensor()`
**Current Location**: 
- `common/utils.py` (lines 107-145) - Already exists
- `API/FalAi/node.py` (lines 220-245) - Duplicate
- `API/Replicate/node.py` (lines 280-302) - Duplicate

**Target Location**: `common/utils.py` (enhance existing)

## Current Implementations (~85% Similar)

### common/utils.py (Existing)
```python
def base64_to_tensor(
    base64_str: str, 
    mode: str = "RGB"
) -> Optional[torch.Tensor]:
    """Convert a base64 image string to a torch.Tensor."""
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
```

### API/FalAi/node.py (Duplicate)
```python
def _base64_to_tensor(self, base64_str):
    """Convert base64 image to tensor."""
    from PIL import Image
    import base64
    
    if not base64_str or not isinstance(base64_str, str):
        return None
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
```

### API/Replicate/node.py (Duplicate)
```python
def _base64_to_tensor(self, base64_str):
    """Convert base64 image to tensor."""
    if not base64_str or not isinstance(base64_str, str):
        return None
    try:
        if "," in base64_str:
            base64_data = base64_str.split(",", 1)[1]
        else:
            base64_data = base64_str

        image_data = base64.b64decode(base64_data, validate=True)
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
```

## Why Extract
- **Duplication Level**: ~85% similar (minor differences in validation)
- **Risk Level**: Low
- **Impact**: High (used in dry run mode and debug)
- **Lines Saved**: ~60 lines (30 lines × 2 files)

## Implementation Steps

### Step 1: Enhance `common/utils.py`
The existing `base64_to_tensor()` function is already good. Just ensure it handles all edge cases:

```python
def base64_to_tensor(
    base64_str: str, 
    mode: str = "RGB"
) -> Optional[torch.Tensor]:
    """
    Convert a base64 image string to a torch.Tensor.
    
    Handles various base64 formats:
    - Data URI format: "data:image/png;base64,..."
    - Raw base64 string: "iVBORw0KGgo..."
    
    Args:
        base64_str: Base64 encoded image data (data URI or raw base64)
        mode: PIL image mode (RGB, RGBA, L, etc.)
        
    Returns:
        torch.Tensor in BxHxWxC format, or None if conversion fails
        
    Examples:
        >>> # From data URI
        >>> tensor = base64_to_tensor("data:image/png;base64,iVBORw0KGgo...")
        >>> tensor.shape
        torch.Size([1, 512, 512, 3])
        
        >>> # From raw base64
        >>> tensor = base64_to_tensor("iVBORw0KGgo...")
        >>> tensor.shape
        torch.Size([1, 512, 512, 3])
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
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_base64_to_tensor()` method definition (lines 220-245)
- Add import: `from common.utils import base64_to_tensor`
- Update method to call the common function:
  ```python
  def _base64_to_tensor(self, base64_str):
      """Convert base64 image to tensor."""
      return base64_to_tensor(base64_str, mode="RGB")
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_base64_to_tensor()` method definition (lines 280-302)
- Add import: `from common.utils import base64_to_tensor`
- Update method to call the common function:
  ```python
  def _base64_to_tensor(self, base64_str):
      """Convert base64 image to tensor."""
      return base64_to_tensor(base64_str, mode="RGB")
  ```

## Testing Checklist

- [ ] Verify function handles data URI format correctly
- [ ] Verify function handles raw base64 string correctly
- [ ] Verify function handles None input correctly
- [ ] Verify function handles empty string correctly
- [ ] Verify function handles invalid base64 correctly
- [ ] Verify function converts to RGB mode correctly
- [ ] Verify function returns correct tensor shape (BxHxWxC)
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `PIL`, `base64`, `io`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
