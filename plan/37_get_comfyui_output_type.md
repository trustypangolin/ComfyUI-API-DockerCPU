# Plan: Extract `get_comfyui_output_type()` and `get_comfyui_input_type()` Functions

## Functions Overview
**Functions**:
1. `get_comfyui_output_type()`
2. `get_comfyui_input_type()`

**Current Location**: 
- `common/type_mapping.py` (lines 220-304) - Already exists

**Target Location**: `common/type_mapping.py` (already there, just document it)

## Current Implementations (Already in common/type_mapping.py)

### get_comfyui_output_type()
```python
def get_comfyui_output_type(api_type: str, output_name: Optional[str] = None, file_url: Optional[str] = None) -> str:
    """
    Convert API schema type to ComfyUI output type.

    Args:
        api_type: Type from API schema (e.g., "image", "audio", "string")
        output_name: Name of the output field (used for fallback detection)
        file_url: URL of the output file (used for file extension detection)

    Returns:
        ComfyUI output type string
    """
    # First, try file extension detection if URL provided
    if file_url:
        file_lower = file_url.lower()
        for ext, comfy_type in FILE_EXTENSION_TO_TYPE.items():
            if file_lower.endswith(ext):
                return comfy_type

    # Normalize type
    normalized_type = api_type.lower().strip() if api_type else ""

    # Direct mapping
    if normalized_type in API_TO_COMFYUI_TYPE_MAP:
        return API_TO_COMFYUI_TYPE_MAP[normalized_type]

    # Check if it's already a valid ComfyUI type
    if normalized_type.upper() in SUPPORTED_OUTPUT_TYPES:
        return normalized_type.upper()

    # Fallback: infer from output name
    if output_name:
        name_lower = output_name.lower()

        # Image-related names
        if any(keyword in name_lower for keyword in ["image", "img", "picture", "photo", "frame"]):
            return "IMAGE"

        # Audio-related names
        if any(keyword in name_lower for keyword in ["audio", "sound", "music", "voice", "speech"]):
            return "AUDIO"

        # Video-related names
        if any(keyword in name_lower for keyword in ["video", "clip", "movie"]):
            return "VIDEO"

        # Conditioning-related names
        if "conditioning" in name_lower:
            return "CONDITIONING"

        # Model-related names
        if any(keyword in name_lower for keyword in ["model", "checkpoint"]):
            return "MODEL"

        # Latent-related names
        if "latent" in name_lower:
            return "LATENT"

    # Default to STRING
    return "STRING"
```

### get_comfyui_input_type()
```python
def get_comfyui_input_type(api_type: str, input_name: Optional[str] = None, file_url: Optional[str] = None) -> str:
    """
    Convert API schema type to ComfyUI input type.

    Similar to get_comfyui_output_type but validates against supported input types.

    Args:
        api_type: Type from API schema (e.g., "image", "audio", "string")
        input_name: Name of the input field (used for fallback detection)
        file_url: URL of the input file (used for file extension detection)

    Returns:
        ComfyUI input type string
    """
    # Get the base type
    comfy_type = get_comfyui_output_type(api_type, input_name, file_url)

    # Validate it's a supported input type
    if comfy_type in SUPPORTED_INPUT_TYPES:
        return comfy_type

    # Fall back to STRING if not a valid input type
    return "STRING"
```

## Why Document
- **Duplication Level**: Already in common/type_mapping.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Functions Exist
The functions already exist in `common/type_mapping.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (functions are only in common/type_mapping.py)

## Testing Checklist

- [x] Verify `get_comfyui_output_type()` converts image types correctly
- [x] Verify `get_comfyui_output_type()` converts audio types correctly
- [x] Verify `get_comfyui_output_type()` converts video types correctly
- [x] Verify `get_comfyui_output_type()` converts string types correctly
- [x] Verify `get_comfyui_output_type()` handles file URL extension detection
- [x] Verify `get_comfyui_output_type()` handles output name fallback
- [x] Verify `get_comfyui_input_type()` validates against supported input types
- [x] Verify `get_comfyui_input_type()` falls back to STRING for invalid types
- [x] Run full test suite for all APIs

## Dependencies
- None (standalone utility functions)

## Rollback Plan
No changes needed (functions already exist).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 15 minutes
- Total: 15 minutes
