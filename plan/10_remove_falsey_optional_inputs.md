# Plan: Extract `remove_falsey_optional_inputs()` Function

## Function Overview
**Function Name**: `remove_falsey_optional_inputs()`
**Current Location**: 
- `API/FalAi/node.py` (lines 162-170)
- `API/Replicate/node.py` (lines 199-208)

**Target Location**: `common/input_handlers.py`

## Current Implementations (~95% Similar)

The implementations are nearly identical, with a minor difference in how they handle empty tensors:

### FalAi Version
```python
def remove_falsey_optional_inputs(self, kwargs):
    """Remove empty/None optional inputs."""
    optional_inputs = self.INPUT_TYPES().get("optional", {})
    for key in list(kwargs.keys()):
        if key in optional_inputs:
            if isinstance(kwargs[key], torch.Tensor):
                continue
            elif not kwargs[key]:
                del kwargs[key]
```

### Replicate Version
```python
def remove_falsey_optional_inputs(self, kwargs):
    """Remove empty/None optional inputs."""
    optional_inputs = self.INPUT_TYPES().get("optional", {})
    for key in list(kwargs.keys()):
        if key in optional_inputs:
            if isinstance(kwargs[key], torch.Tensor):
                if kwargs[key].numel() == 0:
                    del kwargs[key]
            elif not kwargs[key]:
                del kwargs[key]
```

## Why Extract
- **Duplication Level**: ~95% similar (minor difference in tensor handling)
- **Risk Level**: Low
- **Impact**: High (used in all model inputs)
- **Lines Saved**: ~25 lines (12 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/input_handlers.py`
Add the function with unified logic:

```python
def remove_falsey_optional_inputs(
    kwargs: Dict[str, Any],
    optional_inputs: Dict[str, Any]
) -> None:
    """
    Remove empty/None optional inputs.
    
    Modifies kwargs in-place.
    
    Args:
        kwargs: Dictionary of input parameters
        optional_inputs: Dictionary of optional input definitions
        
    Examples:
        >>> kwargs = {"prompt": "test", "seed": None, "steps": 0}
        >>> optional_inputs = {"seed": ..., "steps": ...}
        >>> remove_falsey_optional_inputs(kwargs, optional_inputs)
        >>> kwargs
        {'prompt': 'test'}
    """
    for key in list(kwargs.keys()):
        if key in optional_inputs:
            if isinstance(kwargs[key], torch.Tensor):
                # Keep non-empty tensors, remove empty tensors
                if kwargs[key].numel() == 0:
                    del kwargs[key]
            elif not kwargs[key]:
                # Remove None, empty string, 0, False, etc.
                del kwargs[key]
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `remove_falsey_optional_inputs()` method definition (lines 162-170)
- Add import: `from common.input_handlers import remove_falsey_optional_inputs`
- Update method to call the common function:
  ```python
  def remove_falsey_optional_inputs(self, kwargs):
      """Remove empty/None optional inputs."""
      optional_inputs = self.INPUT_TYPES().get("optional", {})
      remove_falsey_optional_inputs(kwargs, optional_inputs)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `remove_falsey_optional_inputs()` method definition (lines 199-208)
- Add import: `from common.input_handlers import remove_falsey_optional_inputs`
- Update method to call the common function:
  ```python
  def remove_falsey_optional_inputs(self, kwargs):
      """Remove empty/None optional inputs."""
      optional_inputs = self.INPUT_TYPES().get("optional", {})
      remove_falsey_optional_inputs(kwargs, optional_inputs)
  ```

## Testing Checklist

- [ ] Verify function removes None values
- [ ] Verify function removes empty strings
- [ ] Verify function removes 0 values
- [ ] Verify function removes False values
- [ ] Verify function keeps non-empty tensors
- [ ] Verify function removes empty tensors (numel() == 0)
- [ ] Verify function keeps required inputs unchanged
- [ ] Verify function modifies kwargs in-place
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
