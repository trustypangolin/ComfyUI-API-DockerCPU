# Plan: Extract `validate_output_type()` and `validate_input_type()` Functions

## Functions Overview
**Functions**:
1. `validate_output_type()`
2. `validate_input_type()`

**Current Location**: 
- `common/type_mapping.py` (lines 307-330) - Already exists

**Target Location**: `common/type_mapping.py` (already there, just document it)

## Current Implementations (Already in common/type_mapping.py)

### validate_output_type()
```python
def validate_output_type(output_type: str) -> bool:
    """
    Validate that output type is supported by ComfyUI.

    Args:
        output_type: Output type to validate

    Returns:
        True if valid, False otherwise
    """
    return output_type.upper() in SUPPORTED_OUTPUT_TYPES
```

### validate_input_type()
```python
def validate_input_type(input_type: str) -> bool:
    """
    Validate that input type is supported by ComfyUI for inputs.

    Args:
        input_type: Input type to validate

    Returns:
        True if valid, False otherwise
    """
    return input_type.upper() in SUPPORTED_INPUT_TYPES
```

## Why Document
- **Duplication Level**: Already in common/type_mapping.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Functions Exist
The functions already exist in `common/type_mapping.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (functions are only in common/type_mapping.py)

## Testing Checklist

- [x] Verify `validate_output_type()` returns True for valid types
- [x] Verify `validate_output_type()` returns False for invalid types
- [x] Verify `validate_output_type()` is case-insensitive
- [x] Verify `validate_input_type()` returns True for valid types
- [x] Verify `validate_input_type()` returns False for invalid types
- [x] Verify `validate_input_type()` is case-insensitive
- [x] Run full test suite for all APIs

## Dependencies
- None (standalone utility functions)

## Rollback Plan
No changes needed (functions already exist).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
