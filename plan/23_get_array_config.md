# Plan: Extract `get_array_config()` Function

## Function Overview
**Function Name**: `get_array_config()`
**Current Location**: 
- `API/Replicate/schema_to_node.py` (lines 254-278)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to Replicate)

```python
def get_array_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get array configuration for an input field.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration
        
    Returns:
        Dictionary with 'is_array', 'max_items', 'is_optional' or empty dict
    """
    if not model_config:
        return {}
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return {
        'is_array': field_config.get('is_array', False),
        'max_items': field_config.get('max_items'),
        'is_optional': field_config.get('is_optional', False),
    }
```

## Why Extract
- **Duplication Level**: Unique to Replicate (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in Replicate schema conversion)
- **Lines Saved**: ~25 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
def get_array_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get array configuration for an input field.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration (from supported_models.yaml)
        
    Returns:
        Dictionary with array configuration:
        - 'is_array': Whether field is an array
        - 'max_items': Maximum number of items (None if unlimited)
        - 'is_optional': Whether field is optional
        
    Examples:
        >>> config = {"inputs": {"images": {"is_array": True, "max_items": 5}}}
        >>> get_array_config("images", config)
        {'is_array': True, 'max_items': 5, 'is_optional': False}
        >>> get_array_config("prompt", config)
        {'is_array': False, 'max_items': None, 'is_optional': False}
    """
    if not model_config:
        return {}
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return {
        'is_array': field_config.get('is_array', False),
        'max_items': field_config.get('max_items'),
        'is_optional': field_config.get('is_optional', False),
    }
```

### Step 2: Update `API/Replicate/schema_to_node.py`
- Remove the `get_array_config()` function definition (lines 254-278)
- Add import: `from common.schema_utils import get_array_config`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function returns correct array config when available
- [ ] Verify function returns empty dict when model_config is None
- [ ] Verify function returns empty dict when field not found
- [ ] Verify function handles missing keys gracefully
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
