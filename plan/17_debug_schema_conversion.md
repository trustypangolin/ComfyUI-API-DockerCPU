# Plan: Extract `debug_schema_conversion()` Function

## Function Overview
**Function Name**: `debug_schema_conversion()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 467-514)
- `API/Replicate/schema_to_node.py` (lines 381-501)

**Target Location**: `common/debug_utils.py` (NEW FILE)

## Current Implementations (~75% Similar)

The implementations are similar but have differences in how they print debug information:

### FalAi Version
```python
def debug_schema_conversion(schema: Dict, input_types: Dict, return_types: Dict):
    """Debug helper to print INPUT_TYPES and RETURN_TYPES."""
    if not DEBUG_MODE:
        return
    
    fal_model, _ = name_and_version(schema)
    
    print(f"\n{'='*60}")
    print(f"[DEBUG] Schema Conversion for: {fal_model}")
    print(f"{'='*60}")
    
    # Get field patterns from global config
    config = get_config()
    input_mapping = config.get_input_mapping("falai")
    image_fields = [f.lower() for f in input_mapping.get('image_fields', [])]
    audio_fields = [f.lower() for f in input_mapping.get('audio_fields', [])]
    video_fields = [f.lower() for f in input_mapping.get('video_fields', [])]
    
    print(f"\nINPUT (from global_inputs.yaml):")
    inputs_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            type_info = definition[0] if definition else "unknown"
            inputs_found.append(f"  [R] {name}: {type_info}")
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            type_info = definition[0] if definition else "unknown"
            inputs_found.append(f"  [O] {name}: {type_info}")
    
    if inputs_found:
        for line in inputs_found:
            print(line)
    else:
        print("  (none)")
    
    print(f"\nPARAMETERS (from global_parameters.yaml):")
    params_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if params_found:
        for line in params_found:
            print(line)
    else:
        print("  (none)")
    
    print(f"\nOUTPUT: (from global_outputs.yaml):")
    if return_types:
        for name, type_name in return_types.items():
            print(f"  [O] {name}: {type_name}")
    elif input_types:
        print("  (not yet determined - see RETURN_TYPES debug)")
        # Print the raw return_types for debugging
        print(f"  Raw return_types passed: {return_types}")
    else:
        print("  (none)")
```

### Replicate Version
(Similar logic but with more detailed output)

## Why Extract
- **Duplication Level**: ~75% similar (different output formats)
- **Risk Level**: Low
- **Impact**: Low (only used in debug mode)
- **Lines Saved**: ~100 lines (50 lines × 2 files)

## Implementation Steps

### Step 1: Create `common/debug_utils.py`
Create new file with the following content:

```python
"""
Debug utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Debugging schema conversion
- Printing input/output type information
- Validating schema structure
"""

from typing import Dict, Any, Optional

import os


# Debug mode - enabled via DEBUG_API_TRUSTYPANGOLIN environment variable
DEBUG_MODE = os.environ.get("DEBUG_API_TRUSTYPANGOLIN", "false").lower() == "true"


def debug_schema_conversion(
    api_name: str,
    model_name: str,
    input_types: Dict[str, Any],
    return_types: Optional[Dict[str, str]] = None
) -> None:
    """
    Debug helper to print INPUT_TYPES and RETURN_TYPES.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        model_name: Name of the model being converted
        input_types: Generated INPUT_TYPES dictionary
        return_types: Generated RETURN_TYPES dictionary (optional)
        
    Examples:
        >>> debug_schema_conversion("falai", "fal-ai/flux-2/klein/9b/edit", {"required": {"prompt": ("STRING",)}}, {"image": "IMAGE"})
        ============================================================
        [DEBUG] Schema Conversion for: fal-ai/flux-2/klein/9b/edit
        ============================================================
        
        INPUT (from global_inputs.yaml):
          [R] prompt: STRING
        
        PARAMETERS (from global_parameters.yaml):
          (none)
        
        OUTPUT: (from global_outputs.yaml):
          [O] image: IMAGE
    """
    if not DEBUG_MODE:
        return
    
    print(f"\n{'='*60}")
    print(f"[DEBUG] Schema Conversion for: {model_name}")
    print(f"{'='*60}")
    
    # Print INPUT types
    print(f"\nINPUT (from global_inputs.yaml):")
    inputs_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_info = definition[0] if isinstance(definition[0], str) else "COMBO"
                inputs_found.append(f"  [R] {name}: {type_info}")
            elif isinstance(definition, str):
                inputs_found.append(f"  [R] {name}: {definition}")
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_info = definition[0] if isinstance(definition[0], str) else "COMBO"
                inputs_found.append(f"  [O] {name}: {type_info}")
            elif isinstance(definition, str):
                inputs_found.append(f"  [O] {name}: {definition}")
    
    if inputs_found:
        for line in inputs_found:
            print(line)
    else:
        print("  (none)")
    
    # Print PARAMETER types
    print(f"\nPARAMETERS (from global_parameters.yaml):")
    params_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if params_found:
        for line in params_found:
            print(line)
    else:
        print("  (none)")
    
    # Print OUTPUT types
    print(f"\nOUTPUT: (from global_outputs.yaml):")
    if return_types:
        for name, type_name in return_types.items():
            print(f"  [O] {name}: {type_name}")
    elif input_types:
        print("  (not yet determined - see RETURN_TYPES debug)")
        print(f"  Raw return_types passed: {return_types}")
    else:
        print("  (none)")
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `debug_schema_conversion()` function definition (lines 467-514)
- Add import: `from common.debug_utils import debug_schema_conversion`
- Update function to call the common function:
  ```python
  def debug_schema_conversion(schema: Dict, input_types: Dict, return_types: Dict):
      """Debug helper to print INPUT_TYPES and RETURN_TYPES."""
      fal_model, _ = name_and_version(schema)
      debug_schema_conversion("falai", fal_model, input_types, return_types)
  ```

### Step 3: Update `API/Replicate/schema_to_node.py`
- Remove the `debug_schema_conversion()` function definition (lines 381-501)
- Add import: `from common.debug_utils import debug_schema_conversion`
- Update function to call the common function:
  ```python
  def debug_schema_conversion(schema: Dict, input_types: Dict, return_types: Dict):
      """Debug helper to print INPUT_TYPES and RETURN_TYPES."""
      replicate_model, _ = name_and_version(schema)
      debug_schema_conversion("replicate", replicate_model, input_types, return_types)
  ```

## Testing Checklist

- [ ] Verify function prints debug output when DEBUG_MODE is True
- [ ] Verify function does nothing when DEBUG_MODE is False
- [ ] Verify function prints INPUT types correctly
- [ ] Verify function prints PARAMETER types correctly
- [ ] Verify function prints OUTPUT types correctly
- [ ] Verify function handles missing return_types gracefully
- [ ] Test with FalAi API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `os` module for DEBUG_MODE check

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
