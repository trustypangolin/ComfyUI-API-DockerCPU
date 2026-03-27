# Plan: Extract `is_type()` Function

## Function Overview
**Function Name**: `is_type()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 88-92)
- `API/HuggingFace/schema_to_node.py` (lines 45-49)
- `API/Replicate/schema_to_node.py` (lines 119-123)

**Target Location**: `common/utils.py`

## Current Implementation (100% Identical)

```python
def is_type(filename: str, extensions: tuple) -> bool:
    """Check if a filename has one of the given extensions."""
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in extensions)
```

## Why Extract
- **Duplication Level**: 100% identical across all 3 APIs
- **Risk Level**: Very Low
- **Impact**: Low (simple utility function)
- **Lines Saved**: ~15 lines (5 lines × 3 files)

## Implementation Steps

### Step 1: Add to `common/utils.py`
Add the function to `common/utils.py` with enhanced documentation:

```python
def is_type(filename: str, extensions: tuple) -> bool:
    """
    Check if a filename has one of the given extensions.
    
    Args:
        filename: The filename or path to check
        extensions: Tuple of file extensions to match (e.g., (".png", ".jpg"))
        
    Returns:
        True if filename ends with any of the extensions, False otherwise
        
    Examples:
        >>> is_type("image.png", (".png", ".jpg"))
        True
        >>> is_type("image.gif", (".png", ".jpg"))
        False
        >>> is_type("", (".png", ".jpg"))
        False
    """
    if not filename:
        return False
    return any(filename.lower().endswith(ext) for ext in extensions)
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `is_type()` function definition (lines 88-92)
- Add import: `from common.utils import is_type`
- No other changes needed (function signature is identical)

### Step 3: Update `API/HuggingFace/schema_to_node.py`
- Remove the `is_type()` function definition (lines 45-49)
- Add import: `from common.utils import is_type`
- No other changes needed (function signature is identical)

### Step 4: Update `API/Replicate/schema_to_node.py`
- Remove the `is_type()` function definition (lines 119-123)
- Add import: `from common.utils import is_type`
- No other changes needed (function signature is identical)

## Testing Checklist

- [x] Verify `is_type()` works with various file extensions
- [x] Verify `is_type()` handles empty filename correctly
- [x] Verify `is_type()` is case-insensitive
- [x] Run tests for FalAi API
- [x] Run tests for HuggingFace API
- [x] Run tests for Replicate API
- [x] Verify schema conversion still works correctly

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 5 minutes
- Testing: 10 minutes
- Total: 15 minutes
