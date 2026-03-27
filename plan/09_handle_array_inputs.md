# Plan: Extract `handle_array_inputs()` Function

## Function Overview
**Function Name**: `handle_array_inputs()`
**Current Location**: 
- `API/FalAi/node.py` (lines 150-160)
- `API/Replicate/node.py` (lines 187-197)

**Target Location**: `common/input_handlers.py` (NEW FILE)

## Current Implementation (100% Identical)

```python
def handle_array_inputs(self, kwargs):
    """Convert string array inputs to proper arrays."""
    array_inputs = inputs_that_need_arrays(schema)
    for input_name in array_inputs:
        if input_name in kwargs:
            if isinstance(kwargs[input_name], str):
                kwargs[input_name] = (
                    kwargs[input_name].split("\n") if kwargs[input_name] else []
                )
            elif not isinstance(kwargs[input_name], list):
                kwargs[input_name] = [kwargs[input_name]]
```

## Why Extract
- **Duplication Level**: 100% identical in FalAi & Replicate
- **Risk Level**: Low
- **Impact**: High (used in all model inputs)
- **Lines Saved**: ~30 lines (15 lines × 2 files)

## Implementation Steps

### Step 1: Create `common/input_handlers.py`
Create new file with the following content:

```python
"""
Input processing utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Processing array inputs from ComfyUI
- Removing falsey optional inputs
- Converting input images to base64
"""

from typing import Dict, Any, List, Optional

import torch


def handle_array_inputs(
    kwargs: Dict[str, Any],
    array_inputs: List[str]
) -> None:
    """
    Convert string array inputs to proper arrays.
    
    Modifies kwargs in-place.
    
    Args:
        kwargs: Dictionary of input parameters
        array_inputs: List of input names that should be arrays
        
    Examples:
        >>> kwargs = {"images": "url1\nurl2\nurl3"}
        >>> handle_array_inputs(kwargs, ["images"])
        >>> kwargs["images"]
        ['url1', 'url2', 'url3']
        
        >>> kwargs = {"images": "single_url"}
        >>> handle_array_inputs(kwargs, ["images"])
        >>> kwargs["images"]
        ['single_url']
    """
    for input_name in array_inputs:
        if input_name in kwargs:
            if isinstance(kwargs[input_name], str):
                kwargs[input_name] = (
                    kwargs[input_name].split("\n") if kwargs[input_name] else []
                )
            elif not isinstance(kwargs[input_name], list):
                kwargs[input_name] = [kwargs[input_name]]
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `handle_array_inputs()` method definition (lines 150-160)
- Add import: `from common.input_handlers import handle_array_inputs`
- Update method to call the common function:
  ```python
  def handle_array_inputs(self, kwargs):
      """Convert string array inputs to proper arrays."""
      from .schema_to_node import inputs_that_need_arrays
      array_inputs = inputs_that_need_arrays(schema)
      handle_array_inputs(kwargs, array_inputs)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `handle_array_inputs()` method definition (lines 187-197)
- Add import: `from common.input_handlers import handle_array_inputs`
- Update method to call the common function:
  ```python
  def handle_array_inputs(self, kwargs):
      """Convert string array inputs to proper arrays."""
      from .schema_to_node import inputs_that_need_arrays
      array_inputs = inputs_that_need_arrays(schema)
      handle_array_inputs(kwargs, array_inputs)
  ```

## Testing Checklist

- [x] Verify function converts newline-separated strings to arrays
- [x] Verify function converts single strings to single-element arrays
- [x] Verify function converts non-list values to single-element arrays
- [x] Verify function leaves existing arrays unchanged
- [x] Verify function handles empty strings correctly
- [x] Verify function modifies kwargs in-place
- [x] Test with FalAi API
- [x] Test with Replicate API
- [x] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
