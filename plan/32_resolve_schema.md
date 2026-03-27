# Plan: Extract `resolve_schema()` Function

## Function Overview
**Function Name**: `resolve_schema()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 303-322)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to FalAi)

```python
def resolve_schema(prop_data: Dict, openapi_schema: Dict) -> Dict:
    """
    Resolve $ref references in schema.
    
    Args:
        prop_data: Property data that may contain $ref
        openapi_schema: Full OpenAPI schema
        
    Returns:
        Resolved property data
    """
    if "$ref" in prop_data:
        ref_path = prop_data["$ref"].split("/")
        current = openapi_schema
        for path in ref_path[1:]:
            if path not in current:
                return prop_data
            current = current[path]
        return current
    return prop_data
```

## Why Extract
- **Duplication Level**: Unique to FalAi (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in FalAi schema conversion)
- **Lines Saved**: ~20 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
def resolve_schema(prop_data: Dict[str, Any], openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve $ref references in OpenAPI schema.
    
    Args:
        prop_data: Property data that may contain $ref
        openapi_schema: Full OpenAPI schema
        
    Returns:
        Resolved property data (or original if no $ref found)
        
    Examples:
        >>> schema = {"components": {"schemas": {"Image": {"type": "string"}}}}
        >>> prop = {"$ref": "#/components/schemas/Image"}
        >>> resolve_schema(prop, schema)
        {'type': 'string'}
        >>> resolve_schema({"type": "string"}, schema)
        {'type': 'string'}
    """
    if "$ref" in prop_data:
        ref_path = prop_data["$ref"].split("/")
        current = openapi_schema
        for path in ref_path[1:]:
            if path not in current:
                return prop_data
            current = current[path]
        return current
    return prop_data
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `resolve_schema()` function definition (lines 303-322)
- Add import: `from common.schema_utils import resolve_schema`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function resolves $ref correctly
- [ ] Verify function handles missing $ref gracefully
- [ ] Verify function handles invalid $ref path gracefully
- [ ] Verify function returns original data when no $ref found
- [ ] Test with FalAi API
- [ ] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
