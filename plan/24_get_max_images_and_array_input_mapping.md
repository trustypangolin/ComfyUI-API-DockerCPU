# Plan: Extract `get_max_images()` and `get_array_input_mapping()` Functions

## Functions Overview
**Functions**:
1. `get_max_images()`
2. `get_array_input_mapping()`

**Current Location**: 
- `API/Replicate/schema_to_node.py` (lines 126-158)

**Target Location**: `common/schema_utils.py`

## Current Implementations (Unique to Replicate)

### get_max_images()
```python
def get_max_images(model_name: str) -> int:
    """
    Get the max_images setting for a model from configuration.
    
    Args:
        model_name: Full model name with version (e.g., "owner/name:version")
        
    Returns:
        Maximum number of images supported (0 = optional, single image)
    """
    config = get_config()
    
    # Extract model name without version hash
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_max_images("replicate", model_base)
```

### get_array_input_mapping()
```python
def get_array_input_mapping(model_name: str) -> Optional[str]:
    """
    Get the array input field name for a model from configuration.
    
    Args:
        model_name: Full model name with version
        
    Returns:
        Array input field name (e.g., "images") or None
    """
    config = get_config()
    
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_array_input_field("replicate", model_base)
```

## Why Extract
- **Duplication Level**: Unique to Replicate (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in Replicate schema conversion)
- **Lines Saved**: ~35 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add both functions with enhanced documentation:

```python
def get_max_images(api_name: str, model_name: str) -> int:
    """
    Get the max_images setting for a model from configuration.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        model_name: Full model name (may include version hash)
        
    Returns:
        Maximum number of images supported (0 = optional, single image)
        
    Examples:
        >>> get_max_images("replicate", "owner/name:version")
        5
        >>> get_max_images("replicate", "owner/name")
        0
    """
    from common.config_loader import get_config
    
    config = get_config()
    
    # Extract model name without version hash (for Replicate)
    if api_name == "replicate" and ":" in model_name:
        model_name = model_name.split(":")[0]
    
    return config.get_max_images(api_name, model_name)


def get_array_input_mapping(api_name: str, model_name: str) -> Optional[str]:
    """
    Get the array input field name for a model from configuration.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        model_name: Full model name (may include version hash)
        
    Returns:
        Array input field name (e.g., "images") or None
        
    Examples:
        >>> get_array_input_mapping("replicate", "owner/name:version")
        'images'
        >>> get_array_input_mapping("replicate", "owner/name")
        None
    """
    from common.config_loader import get_config
    
    config = get_config()
    
    # Extract model name without version hash (for Replicate)
    if api_name == "replicate" and ":" in model_name:
        model_name = model_name.split(":")[0]
    
    return config.get_array_input_field(api_name, model_name)
```

### Step 2: Update `API/Replicate/schema_to_node.py`
- Remove the `get_max_images()` function definition (lines 126-141)
- Remove the `get_array_input_mapping()` function definition (lines 144-158)
- Add import: `from common.schema_utils import get_max_images, get_array_input_mapping`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `get_max_images("replicate", model_name)`
- Example: `get_array_input_mapping("replicate", model_name)`

## Testing Checklist

- [ ] Verify `get_max_images()` returns correct max images from config
- [ ] Verify `get_max_images()` handles version stripping correctly
- [ ] Verify `get_max_images()` returns 0 when not configured
- [ ] Verify `get_array_input_mapping()` returns correct field name from config
- [ ] Verify `get_array_input_mapping()` handles version stripping correctly
- [ ] Verify `get_array_input_mapping()` returns None when not configured
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in the API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
