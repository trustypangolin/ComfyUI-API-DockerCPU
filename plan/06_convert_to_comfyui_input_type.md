# Plan: Extract `convert_to_comfyui_input_type()` Function

## Function Overview
**Function Name**: `convert_to_comfyui_input_type()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 185-276)
- `API/Replicate/schema_to_node.py` (lines 281-360)

**Target Location**: `common/schema_utils.py`

## Current Implementations (~85% Similar)

The implementations are similar but have some differences:

### FalAi Version
- Takes 7 parameters including `default_example_input`, `items_type`, `items_format`
- Checks for array types with `items_type` and `items_format`
- Uses `TYPE_MAPPING` for fallback

### Replicate Version
- Takes 7 parameters including `default_example_input`, `items_type`, `items_format`
- Checks for array types with `items_type` and `items_format`
- Uses `TYPE_MAPPING` for fallback

### HuggingFace Version
- Takes 5 parameters (no `default_example_input`, `items_type`, `items_format`)
- Simpler logic (no array type handling)
- Uses `TYPE_MAPPING` for fallback

## Why Extract
- **Duplication Level**: ~85% similar (FalAi & Replicate are nearly identical)
- **Risk Level**: Medium (need to handle differences)
- **Impact**: High (used in all schema conversions)
- **Lines Saved**: ~180 lines (90 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Create a unified function that handles all cases:

```python
def convert_to_comfyui_input_type(
    api_name: str,
    input_name: str,
    openapi_type: str,
    openapi_format: Optional[str] = None,
    default_example_input: Optional[Dict] = None,
    items_type: Optional[str] = None,
    items_format: Optional[str] = None,
    config_override: Optional[str] = None,
) -> str:
    """
    Convert OpenAPI type to ComfyUI input type.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        input_name: Name of the input field
        openapi_type: OpenAPI type (string, integer, number, boolean, array)
        openapi_format: OpenAPI format (uri, etc.)
        default_example_input: Example input from schema (for type detection)
        items_type: Type of array items (for array types)
        items_format: Format of array items (for array types)
        config_override: Explicit type from configuration
        
    Returns:
        ComfyUI input type (STRING, INT, FLOAT, BOOLEAN, IMAGE, AUDIO, VIDEO)
        
    Examples:
        >>> convert_to_comfyui_input_type("falai", "image", "string", "uri")
        'IMAGE'
        >>> convert_to_comfyui_input_type("falai", "prompt", "string")
        'STRING'
    """
    from common.config_loader import get_config
    from common.utils import is_type
    
    # Use config override if available
    if config_override:
        return config_override
    
    # Get field patterns from global config
    config = get_config()
    input_mapping = config.get_input_mapping(api_name)
    image_fields = input_mapping.get('image_fields', [])
    audio_fields = input_mapping.get('audio_fields', [])
    video_fields = input_mapping.get('video_fields', [])
    
    # Normalize input name for matching
    input_name_lower = input_name.lower()
    
    # Handle string types
    if openapi_type == "string":
        # Check for URI format or name containing image/audio/video
        if openapi_format == "uri":
            if default_example_input and isinstance(default_example_input, dict):
                if input_name in default_example_input:
                    if is_type(default_example_input[input_name], IMAGE_EXTENSIONS):
                        return "IMAGE"
                    elif is_type(default_example_input[input_name], VIDEO_EXTENSIONS):
                        return "VIDEO"
                    elif is_type(default_example_input[input_name], AUDIO_EXTENSIONS):
                        return "AUDIO"
            # Check against global config patterns
            if any(pattern.lower() in input_name_lower for pattern in image_fields):
                return "IMAGE"
            elif any(pattern.lower() in input_name_lower for pattern in audio_fields):
                return "AUDIO"
            elif any(pattern.lower() in input_name_lower for pattern in video_fields):
                return "VIDEO"
            elif any(x in input_name_lower for x in ["image", "mask"]):
                return "IMAGE"
            elif "audio" in input_name_lower:
                return "AUDIO"
            elif "video" in input_name_lower:
                return "VIDEO"
            else:
                return "STRING"
        elif any(x in input_name_lower for x in ["image", "mask"]):
            return "IMAGE"
        elif "audio" in input_name_lower:
            return "AUDIO"
        elif "video" in input_name_lower:
            return "VIDEO"
        else:
            return "STRING"

    # Handle array types
    if openapi_type == "array" and items_type == "string":
        if items_format == "uri":
            if any(pattern.lower() in input_name_lower for pattern in image_fields):
                return "IMAGE"
            elif any(pattern.lower() in input_name_lower for pattern in audio_fields):
                return "AUDIO"
            elif any(pattern.lower() in input_name_lower for pattern in video_fields):
                return "VIDEO"
        # Also check input name for array types
        if any(x in input_name_lower for x in ["image", "mask"]):
            return "IMAGE"
        elif "audio" in input_name_lower:
            return "AUDIO"
        elif "video" in input_name_lower:
            return "VIDEO"

    # Fallback to TYPE_MAPPING
    TYPE_MAPPING = {
        "string": "STRING",
        "integer": "INT",
        "number": "FLOAT",
        "boolean": "BOOLEAN",
    }
    return TYPE_MAPPING.get(openapi_type, "STRING")
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the `convert_to_comfyui_input_type()` function definition (lines 185-276)
- Add import: `from common.schema_utils import convert_to_comfyui_input_type`
- Update all calls to include `api_name="falai"` as first parameter
- Example: `convert_to_comfyui_input_type("falai", input_name, openapi_type, openapi_format, default_example_input, items_type, items_format, config_override)`

### Step 3: Update `API/Replicate/schema_to_node.py`
- Remove the `convert_to_comfyui_input_type()` function definition (lines 281-360)
- Add import: `from common.schema_utils import convert_to_comfyui_input_type`
- Update all calls to include `api_name="replicate"` as first parameter
- Example: `convert_to_comfyui_input_type("replicate", input_name, openapi_type, openapi_format, default_example_input, items_type, items_format, config_override)`

### Step 4: Update `API/HuggingFace/schema_to_node.py`
- The HuggingFace version is simpler and doesn't use `default_example_input`, `items_type`, `items_format`
- Option A: Keep the HuggingFace version separate (simpler)
- Option B: Update to use the common function with `None` for unused parameters
- **Recommendation**: Option A (keep HuggingFace version separate for now)

## Testing Checklist

- [ ] Verify function returns "IMAGE" for image fields
- [ ] Verify function returns "AUDIO" for audio fields
- [ ] Verify function returns "VIDEO" for video fields
- [ ] Verify function returns "STRING" for text fields
- [ ] Verify function returns "INT" for integer fields
- [ ] Verify function returns "FLOAT" for number fields
- [ ] Verify function returns "BOOLEAN" for boolean fields
- [ ] Verify function handles array types correctly
- [ ] Verify function handles URI format correctly
- [ ] Verify function uses config_override when provided
- [ ] Test with FalAi API (verify api_name="falai" works)
- [ ] Test with Replicate API (verify api_name="replicate" works)
- [ ] Run full test suite for all APIs

## Dependencies
- Depends on `common.config_loader.get_config()`
- Depends on `common.utils.is_type()`
- Requires `IMAGE_EXTENSIONS`, `VIDEO_EXTENSIONS`, `AUDIO_EXTENSIONS` constants

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 25 minutes
- Testing: 30 minutes
- Total: 55 minutes
