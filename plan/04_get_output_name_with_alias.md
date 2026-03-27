# Plan: Extract `get_output_name_with_alias()` Function

## Function Overview
**Function Name**: `get_output_name_with_alias()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 120-159)
- `API/HuggingFace/schema_to_node.py` (lines 89-128)
- `API/Replicate/schema_to_node.py` (lines 189-228)

**Target Location**: `common/schema_utils.py`

## Current Implementations (~95% Similar)

The implementations are nearly identical, with the only difference being the API name passed to `config.get_output_alias()`:

### FalAi Version
```python
alias = config.get_output_alias("falai", "", schema_output_name, output_type, example_url)
```

### HuggingFace Version
```python
alias = config.get_output_alias("huggingface", "", schema_output_name, output_type, example_url)
```

### Replicate Version
```python
alias = config.get_output_alias("replicate", "", schema_output_name, output_type, example_url)
```

## Why Extract
- **Duplication Level**: ~95% similar (only API name differs)
- **Risk Level**: Low
- **Impact**: High (used in all schema conversions)
- **Lines Saved**: ~120 lines (40 lines × 3 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with an `api_name` parameter:

```python
def get_output_name_with_alias(
    api_name: str,
    output_type: str,
    schema_output_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    example_url: Optional[str] = None
) -> str:
    """
    Get the output name, using alias from config if available.
    
    Priority:
    1. Per-model alias in supported_models.yaml
    2. Default alias from global_outputs.yaml
    3. Standardized name from type_mapping
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        output_type: ComfyUI output type (IMAGE, AUDIO, VIDEO, STRING)
        schema_output_name: Original schema output name
        model_config: Model-specific configuration (from supported_models.yaml)
        example_url: Example URL for extension detection
        
    Returns:
        Output name to use (aliased or standardized)
        
    Examples:
        >>> config = {"outputs": {"image": {"alias": "generated_image"}}}
        >>> get_output_name_with_alias("falai", "IMAGE", "image", config)
        'generated_image'
        >>> get_output_name_with_alias("falai", "IMAGE", "image")
        'image'
    """
    from common.config_loader import get_config
    from common.type_mapping import get_standardized_output_name
    
    config = get_config()
    
    # Check per-model alias first
    if model_config:
        outputs = model_config.get('outputs', {})
        for out_name, out_config in outputs.items():
            if out_name.lower() == schema_output_name.lower():
                if 'alias' in out_config:
                    return out_config['alias']
    
    # Check global outputs.yaml for default alias
    alias = config.get_output_alias(api_name, "", schema_output_name, output_type, example_url)
    if alias:
        return alias
    
    # Fall back to standardized name
    return get_standardized_output_name(output_type, schema_output_name)
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_output_name_with_alias()` function definition (lines 120-159)
- Add import: `from common.schema_utils import get_output_name_with_alias`
- Update all calls to include `api_name="falai"` as first parameter
- Example: `get_output_name_with_alias("falai", output_type, schema_output_name, model_config, example_url)`

### Step 3: Update `API/HuggingFace/schema_to_node.py`
- Remove the `get_output_name_with_alias()` function definition (lines 89-128)
- Add import: `from common.schema_utils import get_output_name_with_alias`
- Update all calls to include `api_name="huggingface"` as first parameter
- Example: `get_output_name_with_alias("huggingface", output_type, schema_output_name, model_config, example_url)`

### Step 4: Update `API/Replicate/schema_to_node.py`
- Remove the `get_output_name_with_alias()` function definition (lines 189-228)
- Add import: `from common.schema_utils import get_output_name_with_alias`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `get_output_name_with_alias("replicate", output_type, schema_output_name, model_config, example_url)`

## Testing Checklist

- [ ] Verify function returns alias from model config when available
- [ ] Verify function returns alias from global outputs.yaml when available
- [ ] Verify function returns standardized name when no alias found
- [ ] Verify function handles None model_config correctly
- [ ] Verify function handles empty schema_output_name correctly
- [ ] Test with FalAi API (verify api_name="falai" works)
- [ ] Test with HuggingFace API (verify api_name="huggingface" works)
- [ ] Test with Replicate API (verify api_name="replicate" works)
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`
- Depends on `common.type_mapping.get_standardized_output_name()`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 20 minutes
- Testing: 25 minutes
- Total: 45 minutes
