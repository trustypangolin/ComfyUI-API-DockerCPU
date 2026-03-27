"""
Type mapping module for standardizing ComfyUI INPUT/OUTPUT types across API providers.

This module provides centralized type mapping and validation for converting
API schema types to ComfyUI-compatible types.
"""

from typing import Dict, Any, Optional

# Supported ComfyUI output types (from comfy_api/latest/_io.py)
SUPPORTED_OUTPUT_TYPES = {
    # Core media types
    "IMAGE",
    "AUDIO",
    "VIDEO",

    # Text/prompt types
    "STRING",
    "CONDITIONING",
    "COMBO",

    # Model types
    "MODEL",
    "CLIP",
    "VAE",
    "CLIP_VISION",
    "CLIP_VISION_OUTPUT",
    "STYLE_MODEL",
    "GLIGEN",
    "CONTROL_NET",

    # Latent types
    "LATENT",
    "SAMPLER",
    "SIGMAS",
    "NOISE",
    "GUIDER",

    # Additional types
    "AUDIO_ENCODER",
    "AUDIO_ENCODER_OUTPUT",
    "MASK",
    "BOOLEAN",
    "INT",
    "FLOAT",

    # 3D types
    "VOXEL",
    "MESH",
    "FILE_3D",
    "FILE_3D_GLB",
    "FILE_3D_GLTF",
    "FILE_3D_FBX",
    "FILE_3D_OBJ",
    "FILE_3D_STL",
    "FILE_3D_USDZ",
    "LOAD_3D",
    "LOAD3D_CAMERA",
    "LOAD_3D_ANIMATION",

    # Utility types
    "UPSCALE_MODEL",
    "LATENT_UPSCALE_MODEL",
    "HOOKS",
    "HOOK_KEYFRAMES",
    "TIMESTEPS_RANGE",
    "LATENT_OPERATION",
    "FLOW_CONTROL",
    "ACCUMULATION",
    "PHOTOMAKER",
    "POINT",
    "FACE_ANALYSIS",
    "BBOX",
    "SEGS",
    "MODEL_PATCH",
    "TRACKS",
    "IMAGECOMPARE",
    "COLOR",
    "BOUNDING_BOX",
    "CURVE",
    "HISTOGRAM",
    "SVG",
    "LORA_MODEL",
    "LOSS_MAP",
    "WAN_CAMERA_EMBEDDING",
    "WEBCAM",
}

# Supported ComfyUI input types (subset of output types that can be inputs)
SUPPORTED_INPUT_TYPES = {
    "IMAGE",
    "AUDIO",
    "VIDEO",
    "STRING",
    "CONDITIONING",
    "COMBO",
    "MODEL",
    "CLIP",
    "VAE",
    "CLIP_VISION",
    "STYLE_MODEL",
    "GLIGEN",
    "CONTROL_NET",
    "LATENT",
    "SAMPLER",
    "SIGMAS",
    "NOISE",
    "GUIDER",
    "AUDIO_ENCODER",
    "MASK",
    "BOOLEAN",
    "INT",
    "FLOAT",
    "VOXEL",
    "MESH",
    "UPSCALE_MODEL",
    "LATENT_UPSCALE_MODEL",
    "HOOKS",
    "HOOK_KEYFRAMES",
    "TIMESTEPS_RANGE",
    "LATENT_OPERATION",
    "PHOTOMAKER",
    "POINT",
    "FACE_ANALYSIS",
    "BBOX",
    "SEGS",
    "MODEL_PATCH",
    "TRACKS",
    "COLOR",
    "BOUNDING_BOX",
    "CURVE",
    "HISTOGRAM",
    "SVG",
    "LORA_MODEL",
    "LOSS_MAP",
    "WEBCAM",
}

# Mapping from common API schema types to ComfyUI types
API_TO_COMFYUI_TYPE_MAP = {
    # Image types
    "image": "IMAGE",
    "image_url": "IMAGE",
    "image_uri": "IMAGE",
    "images": "IMAGE",
    "image_inputs": "IMAGE",
    "input_image": "IMAGE",
    "control_image": "IMAGE",
    "mask": "MASK",

    # Audio types
    "audio": "AUDIO",
    "audio_url": "AUDIO",
    "audio_uri": "AUDIO",
    "audio_input": "AUDIO",
    "song_input": "AUDIO",
    "voice_input": "AUDIO",

    # Video types
    "video": "VIDEO",
    "video_url": "VIDEO",
    "video_uri": "VIDEO",
    "video_input": "VIDEO",
    "clip": "VIDEO",

    # Text types
    "string": "STRING",
    "text": "STRING",
    "prompt": "STRING",

    # Conditioning
    "conditioning": "CONDITIONING",

    # Boolean
    "boolean": "BOOLEAN",
    "bool": "BOOLEAN",

    # Integer
    "integer": "INT",
    "int": "INT",

    # Float/Number
    "float": "FLOAT",
    "number": "FLOAT",
    "double": "FLOAT",
}

# File extensions to type mapping
FILE_EXTENSION_TO_TYPE = {
    # Image extensions
    ".png": "IMAGE",
    ".jpg": "IMAGE",
    ".jpeg": "IMAGE",
    ".gif": "IMAGE",
    ".webp": "IMAGE",
    ".bmp": "IMAGE",
    ".tiff": "IMAGE",

    # Audio extensions
    ".mp3": "AUDIO",
    ".wav": "AUDIO",
    ".flac": "AUDIO",
    ".mpga": "AUDIO",
    ".m4a": "AUDIO",
    ".ogg": "AUDIO",
    ".aac": "AUDIO",

    # Video extensions
    ".mp4": "VIDEO",
    ".mkv": "VIDEO",
    ".webm": "VIDEO",
    ".mov": "VIDEO",
    ".mpg": "VIDEO",
    ".mpeg": "VIDEO",
    ".avi": "VIDEO",
    ".flv": "VIDEO",
}


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


def validate_output_type(output_type: str) -> bool:
    """
    Validate that output type is supported by ComfyUI.

    Args:
        output_type: Output type to validate

    Returns:
        True if valid, False otherwise
    """
    return output_type.upper() in SUPPORTED_OUTPUT_TYPES


def validate_input_type(input_type: str) -> bool:
    """
    Validate that input type is supported by ComfyUI for inputs.

    Args:
        input_type: Input type to validate

    Returns:
        True if valid, False otherwise
    """
    return input_type.upper() in SUPPORTED_INPUT_TYPES


def normalize_type_name(type_name: str) -> str:
    """
    Normalize a type name to ComfyUI format (uppercase).

    Args:
        type_name: Type name to normalize

    Returns:
        Normalized type name
    """
    if not type_name:
        return "STRING"

    normalized = type_name.upper().strip()

    # Handle common variations
    variations = {
        "STR": "STRING",
        "TXT": "STRING",
        "BOOL": "BOOLEAN",
        "NUM": "FLOAT",
        "DOUBLE": "FLOAT",
        "IMG": "IMAGE",
        "PIC": "IMAGE",
    }

    if normalized in variations:
        return variations[normalized]

    return normalized


def get_output_type_from_config(output_name: str, outputs_config: Dict[str, Any]) -> Optional[str]:
    """
    Get ComfyUI output type from configuration.

    Args:
        output_name: Name of the output field
        outputs_config: Configuration dictionary for outputs (from supported_models.yaml)

    Returns:
        ComfyUI output type string or None if not configured
    """
    if not outputs_config:
        return None

    output_def = outputs_config.get(output_name, {})
    if not output_def:
        return None

    output_type = output_def.get("type", "STRING")
    return normalize_type_name(output_type)


def get_input_type_from_config(input_name: str, inputs_config: Dict[str, Any]) -> Optional[str]:
    """
    Get ComfyUI input type from configuration.

    Args:
        input_name: Name of the input field
        inputs_config: Configuration dictionary for inputs (from supported_models.yaml)

    Returns:
        ComfyUI input type string or None if not configured
    """
    if not inputs_config:
        return None

    input_def = inputs_config.get(input_name, {})
    if not input_def:
        return None

    input_type = input_def.get("type", "STRING")
    return normalize_type_name(input_type)


def infer_type_from_example(example_value: Any, field_name: Optional[str] = None) -> str:
    """
    Infer ComfyUI type from an example value.

    Args:
        example_value: Example value to infer type from
        field_name: Name of the field (for context)

    Returns:
        ComfyUI type string
    """
    if example_value is None:
        return "STRING" if field_name is None else get_comfyui_output_type("string", field_name)

    # Check for string values that might be URLs/paths
    if isinstance(example_value, str):
        return get_comfyui_output_type("string", field_name, example_value)

    # Check for boolean
    if isinstance(example_value, bool):
        return "BOOLEAN"

    # Check for integer
    if isinstance(example_value, int):
        return "INT"

    # Check for float
    if isinstance(example_value, float):
        return "FLOAT"

    # Check for list/array
    if isinstance(example_value, list):
        if example_value:
            # Try to infer from first element
            element_type = infer_type_from_example(example_value[0], field_name)
            return element_type
        return "STRING"

    # Check for dict
    if isinstance(example_value, dict):
        return "STRING"

    # Default
    return "STRING"


def is_media_type(comfy_type: str) -> bool:
    """
    Check if a type is a media type (IMAGE, AUDIO, VIDEO).

    Args:
        comfy_type: ComfyUI type string

    Returns:
        True if media type, False otherwise
    """
    return comfy_type.upper() in {"IMAGE", "AUDIO", "VIDEO"}


def is_parameter_type(comfy_type: str) -> bool:
    """
    Check if a type is a parameter type (INT, FLOAT, BOOLEAN, STRING).

    Args:
        comfy_type: ComfyUI type string

    Returns:
        True if parameter type, False otherwise
    """
    return comfy_type.upper() in {"INT", "FLOAT", "BOOLEAN", "STRING"}


def get_standardized_output_name(comfy_type: str, output_name_override: Optional[str] = None) -> str:
    """
    Get a standardized output name based on the ComfyUI type.

    Standardized names:
    - IMAGE -> "image"
    - AUDIO -> "audio"
    - VIDEO -> "video"
    - STRING -> "text"
    - CONDITIONING -> "conditioning"
    - Other types use the type in lowercase

    Args:
        comfy_type: ComfyUI type string
        output_name_override: Optional override from config

    Returns:
        Standardized output name string
    """
    # If override provided, use it
    if output_name_override:
        return output_name_override

    # Map type to standardized name
    type_to_name = {
        "IMAGE": "image",
        "AUDIO": "audio",
        "VIDEO": "video",
        "STRING": "text",
        "CONDITIONING": "conditioning",
        "MASK": "mask",
        "LATENT": "latent",
        "MODEL": "model",
        "CLIP": "clip",
        "VAE": "vae",
        "CLIP_VISION": "clip_vision",
    }

    return type_to_name.get(comfy_type.upper(), comfy_type.lower())


def build_standardized_return_dict(
    outputs_config: Dict[str, Any]
) -> Dict[str, str]:
    """
    Build a standardized return type dictionary from config.

    This function ensures that both the output name and type are standardized.

    Args:
        outputs_config: Configuration dictionary for outputs

    Returns:
        Dictionary mapping output names to ComfyUI types
    """
    result = {}

    if outputs_config:
        for output_name, output_def in outputs_config.items():
            output_type = output_def.get('type', 'STRING')
            # Use standardized type
            comfyui_type = get_comfyui_output_type(output_type, output_name)
            # Validate and normalize
            if validate_output_type(comfyui_type):
                # Get standardized name based on type (unless override provided)
                standardized_name = get_standardized_output_name(
                    comfyui_type,
                    output_name  # Use config name as override
                )
                result[standardized_name] = comfyui_type
            else:
                # Fall back to STRING
                result[output_name] = "STRING"

    return result
