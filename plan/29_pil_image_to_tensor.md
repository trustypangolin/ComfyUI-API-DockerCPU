# Plan: Extract `pil_image_to_tensor()` Function

## Function Overview
**Function Name**: `pil_image_to_tensor()`
**Current Location**: 
- `common/utils.py` (lines 235-249) - Already exists

**Target Location**: `common/utils.py` (already there, just document it)

## Current Implementation (Already in common/utils.py)

```python
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

- [x] Verify function converts PIL Image to tensor correctly
- [x] Verify function adds batch dimension
- [x] Verify function permutes to BxHxWxC format
- [x] Verify function converts to float
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`, `PIL`, `torchvision`

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
