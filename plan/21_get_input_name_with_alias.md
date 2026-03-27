# Plan: Extract `get_input_name_with_alias()` Function

## Function Overview
**Function Name**: `get_input_name_with_alias()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 45-85)
- `API/Replicate/schema_to_node.py` (lines 47-87)

**Target Location**: `common/schema_utils.py`

## Current Implementations (100% Identical)

```python
def get_input_name_with_alias(
    input_name: str,
    input_type: str,
    is_array: bool = False,
    array_index: int = 1,
    model_config: Optional[Dict] = None
) -> str:
    """
    Get the input name, using alias from config if available.
    
    Args:
        input_name: Original schema field name
        input_type: ComfyUI type (IMAGE, AUDIO, VIDEO)
        is_array: Whether this is an array input
        array_index: Index for array inputs (1-based)
        model_config: Optional model config override
        
    Returns:
        Alias name if available, otherwise original name
    """
    config = get_config()
    
    # Check for per-model alias override
    if model_config:
        inputs_config = model_config.get('inputs', {})
        for config_name, config_def in inputs_config.items():
            if isinstance(config_def, dict) and config_name.lower() == input_name.lower():
                if 'alias' in config_def:
                    alias = config_def['alias']
                    if is_array:
                        suffix = config_def.get('alias_array_suffix', '_1')
                        return alias + suffix.replace('_1', f'_{array_index}')
                    return alias
    
    # Check global inputs.yaml for alias
    alias = config.get_input_alias("falai", input_name, input_type, is_array, array_index)
    if alias:
        return alias
    
    # Return original name if no alias found
    return input_name
```

## Why Extract
- **Duplication Level**: 100% identical (only API name differs)
- **Risk Level**: Low
- **Impact**: High (used in all schema conversions)
- **Lines Saved**: ~80 lines (40 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with an `api_name` parameter:

```python
def get_input_name_with_alias(
    api_name: str,
    input_name: str,
    input_type: str,
    is_array: bool = False,
    array_index: int = 1,
    model_config: Optional[Dict] = None
) -> str:
    """
    Get the input name, using alias from config if available.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        input_name: Original schema field name
        input_type: ComfyUI type (IMAGE, AUDIO, VIDEO)
        is_array: Whether this is an array input
        array_index: Index for array inputs (1-based)
        model_config: Optional model config override (from supported_models.yaml)
        
    Returns:
        Alias name if available, otherwise original name
        
    Examples:
        >>> config = {"inputs": {"image": {"alias": "input_image"}}}
        >>> get_input_name_with_alias("falai", "image", "IMAGE", model_config=config)
        'input_image'
        >>> get_input_name_with_alias("falai", "prompt", "STRING")
        'prompt'
    """
    from common.config_loader import get_config
    
    config = get_config()
    
    # Check for per-model alias override
    if model_config:
        inputs_config = model_config.get('inputs', {})
        for config_name, config_def in inputs_config.items():
            if isinstance(config_def, dict) and config_name.lower() == input_name.lower():
                if 'alias' in config_def:
                    alias = config_def['alias']
                    if is_array:
                        suffix = config_def.get('alias_array_suffix', '_1')
                        return alias + suffix.replace('_1', f'_{array_index}')
                    return alias
    
    # Check global inputs.yaml for alias
    alias = config.get_input_alias(api_name, input_name, input_type, is_array, array_index)
    if alias:
        return alias
    
    # Return original name if no alias found
    return input_name
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_input_name_with_alias()` function definition (lines 45-85)
- Add import: `from common.schema_utils import get_input_name_with_alias`
- Update all calls to include `api_name="falai"` as first parameter
- Example: `get_input_name_with_alias("falai", input_name, input_type, is_array, array_index, model_config)`

### Step 3: Update `API/Replicate/schema_to_node.py`
- Remove the `get_input_name_with_alias()` function definition (lines 47-87)
- Add import: `from common.schema_utils import get_input_name_with_alias`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `get_input_name_with_alias("replicate", input_name, input_type, is_array, array_index, model_config)`

## Testing Checklist

- [ ] Verify function returns alias from model config when available
- [ ] Verify function returns alias from global inputs.yaml when available
- [ ] Verify function returns original name when no alias found
- [ ] Verify function handles array inputs correctly
- [ ] Verify function handles array index correctly
- [ ] Verify function handles None model_config correctly
- [ ] Test with FalAi API (verify api_name="falai" works)
- [ ] Test with Replicate API (verify api_name="replicate" works)
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
