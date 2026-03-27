# Plan: Extract `inputs_that_need_arrays()` Function

## Function Overview
**Function Name**: `inputs_that_need_arrays()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 337-360)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to FalAi)

```python
def inputs_that_need_arrays(schema: Dict) -> list:
    """
    Find inputs that need array processing.
    
    Args:
        schema: Fal.ai OpenAPI schema
        
    Returns:
        List of input names that should be treated as arrays
    """
    array_inputs = []
    
    # Check components for array types
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    
    for schema_name, schema_data in schemas.items():
        props = schema_data.get("properties", {})
        for prop_name, prop_data in props.items():
            resolved = resolve_schema(prop_data, schema)
            if resolved.get("type") == "array":
                array_inputs.append(prop_name)
    
    return array_inputs
```

## Why Extract
- **Duplication Level**: Unique to FalAi (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in FalAi schema conversion)
- **Lines Saved**: ~25 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
def inputs_that_need_arrays(schema: Dict[str, Any]) -> List[str]:
    """
    Find inputs that need array processing.
    
    Searches through schema components to find properties
    with type "array".
    
    Args:
        schema: OpenAPI schema dictionary
        
    Returns:
        List of input names that should be treated as arrays
        
    Examples:
        >>> schema = {"components": {"schemas": {"Input": {"properties": {"images": {"type": "array"}}}}}}
        >>> inputs_that_need_arrays(schema)
        ['images']
        >>> inputs_that_need_arrays({})
        []
    """
    array_inputs = []
    
    # Check components for array types
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    
    for schema_name, schema_data in schemas.items():
        props = schema_data.get("properties", {})
        for prop_name, prop_data in props.items():
            resolved = resolve_schema(prop_data, schema)
            if resolved.get("type") == "array":
                array_inputs.append(prop_name)
    
    return array_inputs
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `inputs_that_need_arrays()` function definition (lines 337-360)
- Add import: `from common.schema_utils import inputs_that_need_arrays`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function finds array types in components
- [ ] Verify function handles $ref resolution correctly
- [ ] Verify function returns empty list when no arrays found
- [ ] Verify function handles missing components gracefully
- [ ] Test with FalAi API
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `resolve_schema()` function

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
