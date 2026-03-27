# Plan: Extract `get_default_example_input()` Function

## Function Overview
**Function Name**: `get_default_example_input()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 325-334)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to FalAi)

```python
def get_default_example_input(schema: Dict) -> Optional[Dict]:
    """Extract default example input from schema."""
    # Try different locations for example input
    if "default_example_input" in schema:
        return schema["default_example_input"]
    if "x-fal-metadata" in schema.get("info", {}):
        metadata = schema["info"]["x-fal-metadata"]
        if "defaultInput" in metadata:
            return metadata["defaultInput"]
    return {}
```

## Why Extract
- **Duplication Level**: Unique to FalAi (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in FalAi schema conversion)
- **Lines Saved**: ~10 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
def get_default_example_input(schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract default example input from schema.
    
    Tries different locations for example input:
    1. "default_example_input" key at root level
    2. "x-fal-metadata.defaultInput" in info section
    
    Args:
        schema: OpenAPI schema dictionary
        
    Returns:
        Default example input dictionary, or empty dict if not found
        
    Examples:
        >>> schema = {"default_example_input": {"prompt": "test"}}
        >>> get_default_example_input(schema)
        {'prompt': 'test'}
        >>> schema = {"info": {"x-fal-metadata": {"defaultInput": {"prompt": "test"}}}}
        >>> get_default_example_input(schema)
        {'prompt': 'test'}
        >>> get_default_example_input({})
        {}
    """
    # Try different locations for example input
    if "default_example_input" in schema:
        return schema["default_example_input"]
    if "x-fal-metadata" in schema.get("info", {}):
        metadata = schema["info"]["x-fal-metadata"]
        if "defaultInput" in metadata:
            return metadata["defaultInput"]
    return {}
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `get_default_example_input()` function definition (lines 325-334)
- Add import: `from common.schema_utils import get_default_example_input`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function extracts default_example_input from root level
- [ ] Verify function extracts defaultInput from x-fal-metadata
- [ ] Verify function returns empty dict when not found
- [ ] Verify function handles missing keys gracefully
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
