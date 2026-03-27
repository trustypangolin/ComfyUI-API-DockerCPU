# Plan: Extract `_log_input()` Function

## Function Overview
**Function Name**: `_log_input()`
**Current Location**: 
- `API/FalAi/node.py` (lines 286-299)
- `API/Replicate/node.py` (lines 343-358)

**Target Location**: `common/logging_utils.py` (NEW FILE)

## Current Implementations (~90% Similar)

The implementations are nearly identical, with minor differences in how they format values:

### FalAi Version
```python
def _log_input(self, kwargs):
    """Log input parameters."""
    def format_value(v):
        if isinstance(v, list):
            return [format_value(item) for item in v]
        elif isinstance(v, str) and (v.startswith("data:image") or v.startswith("data:audio")):
            comma_idx = v.find(",")
            if comma_idx != -1:
                return v[:comma_idx + 1] + "..."
            return v[:20] + "..."
        return v

    truncated_kwargs = {k: format_value(v) for k, v in kwargs.items()}
    print(f"Running {fal_model} with {truncated_kwargs}")
```

### Replicate Version
```python
def _log_input(self, kwargs):
    """Log input parameters."""
    def format_value(v):
        if isinstance(v, torch.Tensor):
            return f"<Tensor {list(v.shape)} {v.dtype}>"
        elif isinstance(v, list):
            return [format_value(item) for item in v]
        elif isinstance(v, str) and (v.startswith("data:image") or v.startswith("data:audio")):
            comma_idx = v.find(",")
            if comma_idx != -1:
                return v[:comma_idx + 1] + "..."
            return v[:20] + "..."
        return v

    truncated_kwargs = {k: format_value(v) for k, v in kwargs.items()}
    print(f"Running {replicate_model} with {truncated_kwargs}")
```

## Why Extract
- **Duplication Level**: ~90% similar (Replicate handles tensors, FalAi doesn't)
- **Risk Level**: Low
- **Impact**: Medium (used in all model runs)
- **Lines Saved**: ~40 lines (20 lines × 2 files)

## Implementation Steps

### Step 1: Create `common/logging_utils.py`
Create new file with the following content:

```python
"""
Logging utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Formatting input parameters for logging
- Truncating large data like base64 strings
- Logging model execution
"""

from typing import Any, Dict

import torch


def format_value_for_log(value: Any) -> Any:
    """
    Format a value for logging, truncating large data like base64 strings.
    
    Args:
        value: The value to format
        
    Returns:
        Formatted value safe for logging
        
    Examples:
        >>> format_value_for_log("data:image/png;base64,iVBORw0KGgo...")
        'data:image/png;base64,...'
        >>> format_value_for_log(torch.rand(1, 512, 512, 3))
        '<Tensor [1, 512, 512, 3] torch.float32>'
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


def log_input(model_name: str, kwargs: Dict[str, Any]) -> None:
    """
    Log input parameters for a model run.
    
    Args:
        model_name: Name of the model being run
        kwargs: Dictionary of input parameters
        
    Examples:
        >>> log_input("fal-ai/flux-2/klein/9b/edit", {"prompt": "test", "image": "data:image/png;base64,..."})
        Running fal-ai/flux-2/klein/9b/edit with {'prompt': 'test', 'image': 'data:image/png;base64,...'}
    """
    truncated_kwargs = {k: format_value_for_log(v) for k, v in kwargs.items()}
    print(f"Running {model_name} with {truncated_kwargs}")
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_log_input()` method definition (lines 286-299)
- Add import: `from common.logging_utils import log_input`
- Update method to call the common function:
  ```python
  def _log_input(self, kwargs):
      """Log input parameters."""
      log_input(fal_model, kwargs)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_log_input()` method definition (lines 343-358)
- Add import: `from common.logging_utils import log_input`
- Update method to call the common function:
  ```python
  def _log_input(self, kwargs):
      """Log input parameters."""
      log_input(replicate_model, kwargs)
  ```

## Testing Checklist

- [ ] Verify function formats tensor values correctly
- [ ] Verify function formats list values correctly
- [ ] Verify function truncates base64 image strings
- [ ] Verify function truncates base64 audio strings
- [ ] Verify function preserves normal string values
- [ ] Verify function preserves numeric values
- [ ] Verify function prints model name correctly
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `torch`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
