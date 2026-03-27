# Plan: Extract `format_value_for_log()` Function

## Function Overview
**Function Name**: `format_value_for_log()`
**Current Location**: 
- `common/utils.py` (lines 209-232) - Already exists

**Target Location**: `common/utils.py` (already there, just document it)

## Current Implementation (Already in common/utils.py)

```python
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
- `API/FalAi/node.py` - Uses inline `format_value()` function in `_log_input()`
- `API/Replicate/node.py` - Uses inline `format_value()` function in `_log_input()`

These inline functions will be removed when `_log_input()` is refactored to use `common.logging_utils.log_input()`.

## Testing Checklist

- [x] Verify function formats tensor values correctly
- [x] Verify function formats list values correctly
- [x] Verify function truncates base64 image strings
- [x] Verify function truncates base64 audio strings
- [x] Verify function preserves normal string values
- [x] Verify function preserves numeric values
- [x] Run full test suite for all APIs

## Dependencies
- Requires `torch`

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
