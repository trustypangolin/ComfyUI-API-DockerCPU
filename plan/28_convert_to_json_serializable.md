# Plan: Extract `convert_to_json_serializable()` Function

## Function Overview
**Function Name**: `convert_to_json_serializable()`
**Current Location**: 
- `common/utils.py` (lines 186-206) - Already exists

**Target Location**: `common/utils.py` (already there, just document it)

## Current Implementation (Already in common/utils.py)

```python
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

- [x] Verify function converts tensor to shape string
- [x] Verify function converts dict recursively
- [x] Verify function converts list recursively
- [x] Verify function preserves other types
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
