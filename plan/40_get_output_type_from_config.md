# Plan: Extract `get_output_type_from_config()` and `get_input_type_from_config()` Functions

## Functions Overview
**Functions**:
1. `get_output_type_from_config()`
2. `get_input_type_from_config()`

**Current Location**: 
- `common/type_mapping.py` (lines 365-406) - Already exists

**Target Location**: `common/type_mapping.py` (already there, just document it)

## Current Implementations (Already in common/type_mapping.py)

### get_output_type_from_config()
```python
def get_output_type_from_config(output_name: str, outputs_config: Dict[str, Any]) -> Optional[str]:
    """
    Get ComfyUI output type from configuration.

    Args:
        output_name: Name of the output field
        outputs_config: Configuration dictionary for outputs (from supported_models.yaml)

    Returns:
        ComfyUI output type string or None if not configured
    """
    if not outputs_config:
        return None

    output_def = outputs_config.get(output_name, {})
    if not output_def:
        return None

    output_type = output_def.get("type", "STRING")
    return normalize_type_name(output_type)
```

### get_input_type_from_config()
```python
def get_input_type_from_config(input_name: str, inputs_config: Dict[str, Any]) -> Optional[str]:
    """
    Get ComfyUI input type from configuration.

    Args:
        input_name: Name of the input field
        inputs_config: Configuration dictionary for inputs (from supported_models.yaml)

    Returns:
        ComfyUI input type string or None if not configured
    """
    if not inputs_config:
        return None

    input_def = inputs_config.get(input_name, {})
    if not input_def:
        return None

    input_type = input_def.get("type", "STRING")
    return normalize_type_name(input_type)
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

- [x] Verify `get_output_type_from_config()` returns correct type when configured
- [x] Verify `get_output_type_from_config()` returns None when not configured
- [x] Verify `get_output_type_from_config()` handles empty config gracefully
- [x] Verify `get_input_type_from_config()` returns correct type when configured
- [x] Verify `get_input_type_from_config()` returns None when not configured
- [x] Verify `get_input_type_from_config()` handles empty config gracefully
- [x] Run full test suite for all APIs

## Dependencies
- Depends on `normalize_type_name()` function

## Rollback Plan
No changes needed (functions already exist).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
