# Plan: Extract `get_input_type_from_config()` Function

## Function Overview
**Function Name**: `get_input_type_from_config()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 162-182)
- `API/HuggingFace/schema_to_node.py` (lines 66-86)
- `API/Replicate/schema_to_node.py` (lines 231-251)

**Target Location**: `common/schema_utils.py` (NEW FILE)

## Current Implementation (100% Identical)

```python
def get_input_type_from_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Get explicit input type from model configuration.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration
        
    Returns:
        ComfyUI input type or None if not specified
    """
    if not model_config:
        return None
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return field_config.get('type')
```

## Why Extract
- **Duplication Level**: 100% identical across all 3 APIs
- **Risk Level**: Very Low
- **Impact**: Medium (used in schema conversion)
- **Lines Saved**: ~60 lines (20 lines × 3 files)

## Implementation Steps

### Step 1: Create `common/schema_utils.py`
Create new file with the following content:

```python
"""
Schema conversion utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Schema type conversion
- Parameter ordering and grouping
- Model configuration handling
- Output name aliasing
"""

from typing import Dict, Any, Optional, List


def get_input_type_from_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Get explicit input type from model configuration.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration (from supported_models.yaml)
        
    Returns:
        ComfyUI input type (STRING, INT, FLOAT, BOOLEAN, IMAGE, AUDIO, VIDEO)
        or None if not specified in config
        
    Examples:
        >>> config = {"inputs": {"image": {"type": "IMAGE"}}}
        >>> get_input_type_from_config("image", config)
        'IMAGE'
        >>> get_input_type_from_config("prompt", config)
        None
    """
    if not model_config:
        return None
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return field_config.get('type')
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_input_type_from_config()` function definition (lines 162-182)
- Add import: `from common.schema_utils import get_input_type_from_config`
- No other changes needed (function signature is identical)

### Step 3: Update `API/HuggingFace/schema_to_node.py`
- Remove the `get_input_type_from_config()` function definition (lines 66-86)
- Add import: `from common.schema_utils import get_input_type_from_config`
- No other changes needed (function signature is identical)

### Step 4: Update `API/Replicate/schema_to_node.py`
- Remove the `get_input_type_from_config()` function definition (lines 231-251)
- Add import: `from common.schema_utils import get_input_type_from_config`
- No other changes needed (function signature is identical)

## Testing Checklist

- [x] Verify function returns correct type when configured
- [x] Verify function returns None when not configured
- [x] Verify function returns None when model_config is None
- [x] Verify function handles missing 'inputs' key gracefully
- [x] Verify function handles missing field_name gracefully
- [x] Run tests for FalAi API
- [x] Run tests for HuggingFace API
- [x] Run tests for Replicate API
- [x] Verify schema conversion still works correctly

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
