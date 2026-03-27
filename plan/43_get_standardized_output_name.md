# Plan: Extract `get_standardized_output_name()` Function

## Function Overview
**Function Name**: `get_standardized_output_name()`
**Current Location**: 
- `common/type_mapping.py` (lines 481-519) - Already exists

**Target Location**: `common/type_mapping.py` (already there, just document it)

## Current Implementation (Already in common/type_mapping.py)

```python
def get_standardized_output_name(comfy_type: str, output_name_override: Optional[str] = None) -> str:
    """
    Get a standardized output name based on the ComfyUI type.

    Standardized names:
    - IMAGE -> "image"
    - AUDIO -> "audio"
    - VIDEO -> "video"
    - STRING -> "text"
    - CONDITIONING -> "conditioning"
    - Other types use the type in lowercase

    Args:
        comfy_type: ComfyUI type string
        output_name_override: Optional override from config

    Returns:
        Standardized output name string
    """
    # If override provided, use it
    if output_name_override:
        return output_name_override
    
    # Standardized name mapping
    name_map = {
        "IMAGE": "image",
        "AUDIO": "audio",
        "VIDEO": "video",
        "STRING": "text",
        "CONDITIONING": "conditioning",
    }
    
    return name_map.get(comfy_type.upper(), comfy_type.lower())
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

- [x] Verify function returns "image" for IMAGE type
- [x] Verify function returns "audio" for AUDIO type
- [x] Verify function returns "video" for VIDEO type
- [x] Verify function returns "text" for STRING type
- [x] Verify function returns "conditioning" for CONDITIONING type
- [x] Verify function returns lowercase for other types
- [x] Verify function uses override when provided
- [x] Verify function is case-insensitive
- [x] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
No changes needed (function already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
