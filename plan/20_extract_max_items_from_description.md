# Plan: Extract `extract_max_items_from_description()` Function

## Function Overview
**Function Name**: `extract_max_items_from_description()`
**Current Location**: 
- `API/Replicate/schema_to_node.py` (lines 90-116)

**Target Location**: `common/schema_utils.py`

## Current Implementation (Unique to Replicate)

```python
def extract_max_items_from_description(description: str) -> Optional[int]:
    """
    Extract maxItems limit from a description string.
    
    Args:
        description: The description text that may contain "Maximum N images" or similar
        
    Returns:
        The max items count if found, None otherwise
    """
    if not description:
        return None
    
    # Pattern to match "Maximum N images" or "maximum N images"
    patterns = [
        r"maximum\s+(\d+)\s+(?:input\s+)?images?",
        r"max(?:imum)?\s+(\d+)\s+(?:input\s+)?images?",
        r"up\s+to\s+(\d+)\s+(?:input\s+)?images?",
        r"(\d+)\s+images?(?:\s+max(?:imum)?)?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None
```

## Why Extract
- **Duplication Level**: Unique to Replicate (but could be useful for other APIs)
- **Risk Level**: Very Low
- **Impact**: Low (only used in Replicate schema conversion)
- **Lines Saved**: ~30 lines

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add the function with enhanced documentation:

```python
import re
from typing import Optional


def extract_max_items_from_description(description: str) -> Optional[int]:
    """
    Extract maxItems limit from a description string.
    
    Useful for parsing schema descriptions that contain limits like
    "Maximum 5 images" or "Up to 10 input images".
    
    Args:
        description: The description text that may contain max items limit
        
    Returns:
        The max items count if found, None otherwise
        
    Examples:
        >>> extract_max_items_from_description("Maximum 5 images")
        5
        >>> extract_max_items_from_description("Up to 10 input images")
        10
        >>> extract_max_items_from_description("No limit mentioned")
        None
    """
    if not description:
        return None
    
    # Pattern to match "Maximum N images" or "maximum N images"
    patterns = [
        r"maximum\s+(\d+)\s+(?:input\s+)?images?",
        r"max(?:imum)?\s+(\d+)\s+(?:input\s+)?images?",
        r"up\s+to\s+(\d+)\s+(?:input\s+)?images?",
        r"(\d+)\s+images?(?:\s+max(?:imum)?)?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None
```

### Step 2: Update `API/Replicate/schema_to_node.py`
- Remove the `extract_max_items_from_description()` function definition (lines 90-116)
- Add import: `from common.schema_utils import extract_max_items_from_description`
- No other changes needed (function signature is identical)

## Testing Checklist

- [ ] Verify function extracts "Maximum N images" correctly
- [ ] Verify function extracts "Up to N input images" correctly
- [ ] Verify function extracts "N images max" correctly
- [ ] Verify function is case-insensitive
- [ ] Verify function returns None when no limit found
- [ ] Verify function returns None for empty description
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- Requires `re` module

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 10 minutes
- Testing: 15 minutes
- Total: 25 minutes
