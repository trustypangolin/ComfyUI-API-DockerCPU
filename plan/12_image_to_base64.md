# Plan: Enhance `image_to_base64()` Function

## Function Overview
**Function Name**: `image_to_base64()` and `_image_to_base64()`
**Current Location**: 
- `common/utils.py` (lines 20-44) - Already exists
- `API/FalAi/node.py` (lines 103-124) - Duplicate
- `API/Replicate/node.py` (lines 131-163) - Duplicate

**Target Location**: `common/utils.py` (enhance existing)

## Current Implementations (~80% Similar)

### common/utils.py (Existing)
```python
def image_to_base64(image: Union[Image.Image, torch.Tensor]) -> str:
    """Convert a PIL Image or tensor to a base64 encoded data URI."""
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
```

### API/FalAi/node.py (Duplicate)
```python
def _image_to_base64(self, image):
    """Convert image tensor to base64 data URI."""
    import base64
    from PIL import Image
    
    if isinstance(image, torch.Tensor):
        if image.dim() == 4:
            image = image.squeeze(0)
        if image.size(0) in [1, 3, 4]:
            image = image.permute(1, 2, 0)
        to_pil = transforms.ToPILImage()
        pil_image = to_pil(image) if image.max() <= 1.0 else to_pil(image.div(255))
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
    else:
        pil_image = image

    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
```

### API/Replicate/node.py (Duplicate)
```python
def _image_to_base64(self, image):
    """Convert image tensor to base64 data URI."""
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
    img_str = base64_encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
```

## Why Extract
- **Duplication Level**: ~80% similar (different normalization approaches)
- **Risk Level**: Medium (need to unify normalization logic)
- **Impact**: High (used in all image processing)
- **Lines Saved**: ~60 lines (30 lines × 2 files)

## Implementation Steps

### Step 1: Enhance `common/utils.py`
Update the existing `image_to_base64()` function to handle all cases:

```python
def image_to_base64(image: Union[Image.Image, torch.Tensor]) -> str:
    """
    Convert a PIL Image or tensor to a base64 encoded data URI.
    
    Handles various tensor formats:
    - 4D tensor (BxCxHxW) -> squeezes to 3D
    - 3D tensor (CxHxW) -> permutes to HxWxC
    - 3D tensor (HxWxC) -> uses directly
    - Normalizes values to 0-255 range if needed
    
    Args:
        image: PIL Image or torch.Tensor (various formats)
        
    Returns:
        Base64 encoded data URI string (data:image/png;base64,...)
        
    Examples:
        >>> # From tensor
        >>> tensor = torch.rand(1, 512, 512, 3)
        >>> data_uri = image_to_base64(tensor)
        >>> data_uri.startswith("data:image/png;base64,")
        True
        
        >>> # From PIL Image
        >>> pil_image = Image.new("RGB", (512, 512))
        >>> data_uri = image_to_base64(pil_image)
        >>> data_uri.startswith("data:image/png;base64,")
        True
    """
    if isinstance(image, torch.Tensor):
        # Handle different tensor formats
        if image.dim() == 4:  # BxCxHxW
            image = image.squeeze(0)
        if image.size(0) in [1, 3, 4]:  # CxHxW format
            image = image.permute(1, 2, 0)
        
        # Normalize to 0-255 range if needed
        if image.max() <= 1.0:
            image = (image * 255).clip(0, 255).to(torch.uint8)
        else:
            image = image.clip(0, 255).to(torch.uint8)
        
        # Convert to PIL Image
        image = Image.fromarray(image.cpu().numpy())
    
    # Ensure RGB format
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    # Save to buffer
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    
    # Encode to base64
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_image_to_base64()` method definition (lines 103-124)
- Add import: `from common.utils import image_to_base64`
- Update method to call the common function:
  ```python
  def _image_to_base64(self, image):
      """Convert image tensor to base64 data URI."""
      return image_to_base64(image)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_image_to_base64()` method definition (lines 131-163)
- Add import: `from common.utils import image_to_base64`
- Update method to call the common function:
  ```python
  def _image_to_base64(self, image):
      """Convert image tensor to base64 data URI."""
      return image_to_base64(image)
  ```

## Testing Checklist

- [ ] Verify function handles 4D tensor (BxCxHxW) correctly
- [ ] Verify function handles 3D tensor (CxHxW) correctly
- [ ] Verify function handles 3D tensor (HxWxC) correctly
- [ ] Verify function normalizes 0-1 range to 0-255
- [ ] Verify function handles 0-255 range correctly
- [ ] Verify function handles grayscale images
- [ ] Verify function handles RGBA images
- [ ] Verify function handles PIL Image input
- [ ] Verify function returns correct base64 data URI format
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `PIL`, `base64`, `io`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
