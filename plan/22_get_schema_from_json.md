# Plan: Extract `get_schema_from_json()` Function

## Function Overview
**Function Name**: `get_schema_from_json()`
**Current Location**: 
- `API/HuggingFace/schema_to_node.py` (lines 229-243)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to HuggingFace)

```python
def get_schema_from_json(schema_path: str) -> Optional[Dict]:
    """
    Load a schema from a JSON file.
    
    Args:
        schema_path: Path to the JSON schema file
        
    Returns:
        Schema dictionary or None if loading fails
    """
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
```

## Why Extract
- **Duplication Level**: Unique to HuggingFace (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in HuggingFace schema loading)
- **Lines Saved**: ~15 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
import json
from typing import Optional, Dict, Any


def get_schema_from_json(schema_path: str) -> Optional[Dict[str, Any]]:
    """
    Load a schema from a JSON file.
    
    Args:
        schema_path: Path to the JSON schema file
        
    Returns:
        Schema dictionary or None if loading fails
        
    Examples:
        >>> schema = get_schema_from_json("schemas/HuggingFace/model.json")
        >>> schema is not None
        True
        >>> get_schema_from_json("nonexistent.json") is None
        True
    """
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
```

### Step 2: Update `API/HuggingFace/schema_to_node.py`
- Remove the `get_schema_from_json()` function definition (lines 229-243)
- Add import: `from common.schema_utils import get_schema_from_json`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function loads valid JSON file correctly
- [ ] Verify function returns None for nonexistent file
- [ ] Verify function returns None for invalid JSON
- [ ] Verify function handles UTF-8 encoding correctly
- [ ] Test with HuggingFace API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `json` module

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
