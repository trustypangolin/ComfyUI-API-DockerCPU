# Plan: Extract `get_standard_parameters()` Function

## Function Overview
**Function Name**: `get_standard_parameters()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 109-117)
- `API/Replicate/schema_to_node.py` (lines 178-186)

**Target Location**: `common/schema_utils.py`

## Current Implementation (100% Identical)

```python
def get_standard_parameters() -> Dict[str, Any]:
    """
    Get standard parameters for nodes.
    
    Returns:
        Dictionary of standard parameter definitions
    """
    config = get_config()
    return config.get_standard_parameters("falai")  # or "replicate"
```

## Why Extract
- **Duplication Level**: 100% identical (only API name differs)
- **Risk Level**: Very Low
- **Impact**: Low (used in schema conversion)
- **Lines Saved**: ~25 lines (12 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with an `api_name` parameter:

```python
def get_standard_parameters(api_name: str) -> Dict[str, Any]:
    """
    Get standard parameters for nodes.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        
    Returns:
        Dictionary of standard parameter definitions from global_parameters.yaml
        
    Examples:
        >>> params = get_standard_parameters("falai")
        >>> "seed" in params
        True
        >>> "steps" in params
        True
    """
    from common.config_loader import get_config
    
    config = get_config()
    return config.get_standard_parameters(api_name)
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_standard_parameters()` function definition (lines 109-117)
- Add import: `from common.schema_utils import get_standard_parameters`
- Update all calls to include `api_name="falai"` as first parameter
- Example: `get_standard_parameters("falai")`

### Step 3: Update `API/Replicate/schema_to_node.py`
- Remove the `get_standard_parameters()` function definition (lines 178-186)
- Add import: `from common.schema_utils import get_standard_parameters`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `get_standard_parameters("replicate")`

## Testing Checklist

- [x] Verify function returns standard parameters for FalAi
- [x] Verify function returns standard parameters for Replicate
- [x] Verify function returns empty dict when no parameters defined
- [x] Test with FalAi API
- [x] Test with Replicate API
- [x] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
