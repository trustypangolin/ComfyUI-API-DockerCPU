# Plan: Extract `normalize_type_name()` Function

## Function Overview
**Function Name**: `normalize_type_name()`
**Current Location**: 
- `common/type_mapping.py` (lines 333-362) - Already exists

**Target Location**: `common/type_mapping.py` (already there, just document it)

## Current Implementation (Already in common/type_mapping.py)

```python
def normalize_type_name(type_name: str) -> str:
    """
    Normalize a type name to ComfyUI format (uppercase).

    Args:
        type_name: Type name to normalize

    Returns:
        Normalized type name
    """
    if not type_name:
        return "STRING"

    normalized = type_name.upper().strip()

    # Handle common variations
    variations = {
        "STR": "STRING",
        "TXT": "STRING",
        "BOOL": "BOOLEAN",
        "NUM": "FLOAT",
        "DOUBLE": "FLOAT",
        "IMG": "IMAGE",
        "PIC": "IMAGE",
    }

    if normalized in variations:
        return variations[normalized]

    return normalized
```

## Why Document
- **Duplication Level**: Already in common/type_mapping.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Function Exists
The function already exists in `common/type_mapping.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (function is only in common/type_mapping.py)

## Testing Checklist

- [x] Verify function normalizes "str" to "STRING"
- [x] Verify function normalizes "txt" to "STRING"
- [x] Verify function normalizes "bool" to "BOOLEAN"
- [x] Verify function normalizes "num" to "FLOAT"
- [x] Verify function normalizes "double" to "FLOAT"
- [x] Verify function normalizes "img" to "IMAGE"
- [x] Verify function normalizes "pic" to "IMAGE"
- [x] Verify function handles empty string correctly
- [x] Verify function handles None correctly
- [x] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
