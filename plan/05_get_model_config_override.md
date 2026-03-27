# Plan: Extract `get_model_config_override()` Function

## Function Overview
**Function Name**: `get_model_config_override()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 95-106)
- `API/HuggingFace/schema_to_node.py` (lines 52-63)
- `API/Replicate/schema_to_node.py` (lines 161-175)

**Target Location**: `common/schema_utils.py`

## Current Implementations (~90% Similar)

The implementations are nearly identical, with the only difference being the API name passed to `config.get_model_config()`:

### FalAi Version
```python
def get_model_config_override(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        model_id: Model identifier (e.g., "fal-ai/flux-2/klein/9b/edit")
        
    Returns:
        Model configuration dictionary or None
    """
    config = get_config()
    return config.get_model_config("falai", model_id)
```

### HuggingFace Version
```python
def get_model_config_override(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        model_id: Model identifier (e.g., "renderartist/Technically-Color-Z-Image-Turbo")
        
    Returns:
        Model configuration dictionary or None
    """
    config = get_config()
    return config.get_model_config("huggingface", model_id)
```

### Replicate Version
```python
def get_model_config_override(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        model_name: Full model name with version
        
    Returns:
        Model configuration dictionary or None
    """
    config = get_config()
    
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_model_config("replicate", model_base)
```

## Why Extract
- **Duplication Level**: ~90% similar (only API name differs, Replicate has extra version stripping)
- **Risk Level**: Low
- **Impact**: High (used in all schema conversions)
- **Lines Saved**: ~45 lines (15 lines × 3 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with an `api_name` parameter and handle Replicate's version stripping:

```python
def get_model_config_override(
    api_name: str,
    model_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        model_id: Model identifier (e.g., "fal-ai/flux-2/klein/9b/edit" or "owner/name:version")
        
    Returns:
        Model configuration dictionary from supported_models.yaml, or None if not found
        
    Examples:
        >>> config = get_model_config_override("falai", "fal-ai/flux-2/klein/9b/edit")
        >>> config is not None
        True
        >>> get_model_config_override("falai", "nonexistent/model") is None
        True
    """
    from common.config_loader import get_config
    
    config = get_config()
    
    # For Replicate, strip version hash if present (e.g., "owner/name:version" -> "owner/name")
    if api_name == "replicate" and ":" in model_id:
        model_id = model_id.split(":")[0]
    
    return config.get_model_config(api_name, model_id)
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_model_config_override()` function definition (lines 95-106)
- Add import: `from common.schema_utils import get_model_config_override`
- Update all calls to include `api_name="falai"` as first parameter
- Example: `get_model_config_override("falai", model_id)`

### Step 3: Update `API/HuggingFace/schema_to_node.py`
- Remove the `get_model_config_override()` function definition (lines 52-63)
- Add import: `from common.schema_utils import get_model_config_override`
- Update all calls to include `api_name="huggingface"` as first parameter
- Example: `get_model_config_override("huggingface", model_id)`

### Step 4: Update `API/Replicate/schema_to_node.py`
- Remove the `get_model_config_override()` function definition (lines 161-175)
- Add import: `from common.schema_utils import get_model_config_override`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `get_model_config_override("replicate", model_name)`
- Note: The version stripping is now handled internally by the common function

## Testing Checklist

- [ ] Verify function returns config when model exists in supported_models.yaml
- [ ] Verify function returns None when model doesn't exist
- [ ] Verify function handles Replicate version stripping correctly (e.g., "owner/name:version" -> "owner/name")
- [ ] Verify function handles FalAi model IDs correctly
- [ ] Verify function handles HuggingFace model IDs correctly
- [ ] Test with FalAi API (verify api_name="falai" works)
- [ ] Test with HuggingFace API (verify api_name="huggingface" works)
- [ ] Test with Replicate API (verify api_name="replicate" works)
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
