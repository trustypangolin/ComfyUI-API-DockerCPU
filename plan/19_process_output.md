# Plan: Extract `_process_output()` Function

## Function Overview
**Function Name**: `_process_output()`
**Current Location**: 
- `API/FalAi/node.py` (lines 341-367)
- `API/Replicate/node.py` (lines 398-422)

**Target Location**: `common/output_handlers.py`

## Current Implementations (~85% Similar)

The implementations are similar but have minor differences in how they handle output values:

### FalAi Version
```python
def _process_output(self, output, return_type):
    """Process API output into ComfyUI format."""
    processed_outputs = []
    
    if isinstance(return_type, dict):
        for prop_name, prop_type in return_type.items():
            if prop_type == "IMAGE":
                processed_outputs.append(self.handle_image_output(output.get(prop_name)))
            elif prop_type == "AUDIO":
                processed_outputs.append(self.handle_audio_output(output.get(prop_name)))
            elif prop_type == "VIDEO_URI":
                processed_outputs.append(output.get(prop_name))
            elif prop_type == "STRING":
                val = output.get(prop_name, "")
                processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else str(val))
            else:
                processed_outputs.append(output.get(prop_name, ""))
    else:
        if return_type == "IMAGE":
            processed_outputs.append(self.handle_image_output(output))
        elif return_type == "AUDIO":
            processed_outputs.append(self.handle_audio_output(output))
        else:
            val = output if isinstance(output, (list, tuple)) else str(output)
            processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else val)

    return processed_outputs
```

### Replicate Version
```python
def _process_output(self, output, return_type):
    """Process API output into ComfyUI format."""
    processed_outputs = []
    
    if isinstance(return_type, dict):
        for prop_name, prop_type in return_type.items():
            if prop_type == "IMAGE":
                processed_outputs.append(self.handle_image_output(output.get(prop_name)))
            elif prop_type == "AUDIO":
                processed_outputs.append(self.handle_audio_output(output.get(prop_name)))
            elif prop_type == "STRING":
                val = output.get(prop_name, "")
                processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else str(val))
            else:
                processed_outputs.append(output.get(prop_name, ""))
    else:
        if return_type == "IMAGE":
            processed_outputs.append(self.handle_image_output(output))
        elif return_type == "AUDIO":
            processed_outputs.append(self.handle_audio_output(output))
        else:
            val = output if isinstance(output, (list, tuple)) else str(output)
            processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else val)

    return processed_outputs
```

## Why Extract
- **Duplication Level**: ~85% similar (FalAi has VIDEO_URI handling)
- **Risk Level**: Medium (need to handle different output types)
- **Impact**: High (used in all model outputs)
- **Lines Saved**: ~80 lines (40 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/output_handlers.py`
Add the function with handler function parameters:

```python
def process_output(
    output: Any,
    return_type: Union[Dict[str, str], str],
    handle_image_func: callable,
    handle_audio_func: callable
) -> List[Any]:
    """
    Process API output into ComfyUI format.
    
    Args:
        output: API output (dict or single value)
        return_type: Return type specification (dict or string)
        handle_image_func: Function to process image outputs
        handle_audio_func: Function to process audio outputs
        
    Returns:
        List of processed outputs matching the return type
        
    Examples:
        >>> output = {"image": file_obj, "text": "result"}
        >>> return_type = {"image": "IMAGE", "text": "STRING"}
        >>> outputs = process_output(output, return_type, handle_image_output, handle_audio_output)
        >>> len(outputs)
        2
    """
    processed_outputs = []
    
    if isinstance(return_type, dict):
        for prop_name, prop_type in return_type.items():
            if prop_type == "IMAGE":
                processed_outputs.append(handle_image_func(output.get(prop_name)))
            elif prop_type == "AUDIO":
                processed_outputs.append(handle_audio_func(output.get(prop_name)))
            elif prop_type == "VIDEO_URI":
                processed_outputs.append(output.get(prop_name))
            elif prop_type == "STRING":
                val = output.get(prop_name, "")
                processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else str(val))
            else:
                processed_outputs.append(output.get(prop_name, ""))
    else:
        if return_type == "IMAGE":
            processed_outputs.append(handle_image_func(output))
        elif return_type == "AUDIO":
            processed_outputs.append(handle_audio_func(output))
        else:
            val = output if isinstance(output, (list, tuple)) else str(output)
            processed_outputs.append("".join(list(val)).strip() if isinstance(val, (list, tuple)) else val)

    return processed_outputs
```

### Step 2: Update `API/FalAi/node.py`
- Remove the `_process_output()` method definition (lines 341-367)
- Add import: `from common.output_handlers import process_output`
- Update method to call the common function:
  ```python
  def _process_output(self, output, return_type):
      """Process API output into ComfyUI format."""
      return process_output(output, return_type, self.handle_image_output, self.handle_audio_output)
  ```

### Step 3: Update `API/Replicate/node.py`
- Remove the `_process_output()` method definition (lines 398-422)
- Add import: `from common.output_handlers import process_output`
- Update method to call the common function:
  ```python
  def _process_output(self, output, return_type):
      """Process API output into ComfyUI format."""
      return process_output(output, return_type, self.handle_image_output, self.handle_audio_output)
  ```

## Testing Checklist

- [ ] Verify function processes IMAGE outputs correctly
- [ ] Verify function processes AUDIO outputs correctly
- [ ] Verify function processes VIDEO_URI outputs correctly
- [ ] Verify function processes STRING outputs correctly
- [ ] Verify function handles dict return type
- [ ] Verify function handles string return type
- [ ] Verify function handles list/tuple values correctly
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `handle_image_output()` and `handle_audio_output()` functions

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
