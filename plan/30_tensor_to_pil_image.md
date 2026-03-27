# Plan: Extract `tensor_to_pil_image()` Function

## Function Overview
**Function Name**: `tensor_to_pil_image()`
**Current Location**: 
- `common/utils.py` (lines 47-62) - Already exists

**Target Location**: `common/utils.py` (already there, just document it)

## Current Implementation (Already in common/utils.py)

```python
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
```

## Why Document
- **Duplication Level**: Already in common/utils.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Function Exists
The function already exists in `common/utils.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (function is only in common/utils.py)

## Testing Checklist

- [x] Verify function converts 3D tensor (CxHxW) to PIL Image correctly
- [x] Verify function converts 2D tensor (HxW) to PIL Image correctly
- [x] Verify function handles grayscale (1 channel) correctly
- [x] Verify function handles RGB (3 channels) correctly
- [x] Verify function handles RGBA (4 channels) correctly
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `PIL`, `torchvision`

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
