# Plan: Extract `combine_split_image_inputs()` Function

## Function Overview
**Function Name**: `combine_split_image_inputs()`
**Current Location**: 
- `API/Replicate/node.py` (lines 210-230)

**Target Location**: `common/input_handlers.py`

## Current Implementation (Unique to Replicate)

```python
def combine_split_image_inputs(self, kwargs):
    """Combine split image inputs back into arrays."""
    max_images = get_max_images(replicate_model)
    if max_images == 0:
        return

    array_input_name = get_array_input_mapping(replicate_model)
    if not array_input_name:
        return

    base_name = array_input_name.replace("images", "image").replace("_url", "")
    split_inputs = []
    
    for i in range(1, max_images + 1):
        input_name = f"{base_name}_{i}"
        if input_name in kwargs and kwargs[input_name] is not None:
            split_inputs.append(kwargs[input_name])
            del kwargs[input_name]

    if split_inputs:
        kwargs[array_input_name] = split_inputs
```

## Why Extract
- **Duplication Level**: Unique to Replicate (but could be useful for other APIs)
- **Risk Level**: Low
- **Impact**: Medium (used in Replicate model inputs)
- **Lines Saved**: ~25 lines

## Implementation Steps

### Step 1: Add to `common/input_handlers.py`
Add the function with helper function parameters:

```python
def combine_split_image_inputs(
    kwargs: Dict[str, Any],
    max_images: int,
    array_input_name: Optional[str]
) -> None:
    """
    Combine split image inputs back into arrays.
    
    Modifies kwargs in-place.
    
    Args:
        kwargs: Dictionary of input parameters
        max_images: Maximum number of images (0 = no combining)
        array_input_name: Name of the array input field (e.g., "images")
        
    Examples:
        >>> kwargs = {"image_1": "url1", "image_2": "url2", "image_3": "url3"}
        >>> combine_split_image_inputs(kwargs, 3, "images")
        >>> kwargs["images"]
        ['url1', 'url2', 'url3']
        >>> "image_1" in kwargs
        False
    """
    if max_images == 0:
        return

    if not array_input_name:
        return

    base_name = array_input_name.replace("images", "image").replace("_url", "")
    split_inputs = []
    
    for i in range(1, max_images + 1):
        input_name = f"{base_name}_{i}"
        if input_name in kwargs and kwargs[input_name] is not None:
            split_inputs.append(kwargs[input_name])
            del kwargs[input_name]

    if split_inputs:
        kwargs[array_input_name] = split_inputs
```

### Step 2: Update `API/Replicate/node.py`
- Remove the `combine_split_image_inputs()` method definition (lines 210-230)
- Add import: `from common.input_handlers import combine_split_image_inputs`
- Update method to call the common function:
  ```python
  def combine_split_image_inputs(self, kwargs):
      """Combine split image inputs back into arrays."""
      from .schema_to_node import get_max_images, get_array_input_mapping
      max_images = get_max_images(replicate_model)
      array_input_name = get_array_input_mapping(replicate_model)
      combine_split_image_inputs(kwargs, max_images, array_input_name)
  ```

## Testing Checklist

- [ ] Verify function combines split images correctly
- [ ] Verify function removes split input keys
- [ ] Verify function handles max_images=0 correctly
- [ ] Verify function handles None array_input_name correctly
- [ ] Verify function handles missing split inputs gracefully
- [ ] Verify function modifies kwargs in-place
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- None (standalone utility function)

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definition in the API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
