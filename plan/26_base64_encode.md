# Plan: Extract `base64_encode()` Function

## Function Overview
**Function Name**: `base64_encode()`
**Current Location**: 
- `API/Replicate/node.py` (lines 427-430)

**Target Location**: `common/utils.py`

## Current Implementation (Unique to Replicate)

```python
def base64_encode(data):
    """Base64 encode data."""
    import base64
    return base64.b64encode(data)
```

## Why Extract
- **Duplication Level**: Unique to Replicate (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in Replicate)
- **Lines Saved**: ~5 lines

## Implementation Steps

### Step 1: Add to `common/utils.py`
Add the function with enhanced documentation:

```python
def base64_encode(data: bytes) -> bytes:
    """
    Base64 encode data.
    
    Args:
        data: Bytes to encode
        
    Returns:
        Base64 encoded bytes
        
    Examples:
        >>> base64_encode(b"hello world")
        b'aGVsbG8gd29ybGQ='
    """
    import base64
    return base64.b64encode(data)
```

### Step 2: Update `API/Replicate/node.py`
- Remove the `base64_encode()` function definition (lines 427-430)
- Add import: `from common.utils import base64_encode`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function encodes bytes correctly
- [ ] Verify function handles empty bytes correctly
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `base64` module

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 5 minutes
- Testing: 10 minutes
- Total: 15 minutes
