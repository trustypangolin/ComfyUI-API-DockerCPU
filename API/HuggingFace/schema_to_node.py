"""
Schema to Node converter for HuggingFace API

Translates HuggingFace's model schemas into ComfyUI INPUT_TYPES format.
Note: HuggingFace models execute locally in ComfyUI, so they don't use
dry_run/force_rerun parameters (they execute immediately).

Uses YAML configuration for model-specific settings.
"""

import json
import os
import sys
from typing import Dict, Any, Optional

# Import the configuration loader - use absolute import with sys.path fallback
# This handles both installed package and direct execution scenarios
try:
    from common.config_loader import get_config, ConfigLoader
    from common.type_mapping import get_comfyui_output_type, validate_output_type, get_standardized_output_name
    from common.utils import is_type
    from common.schema_utils import get_input_type_from_config
except ImportError:
    # Add parent directory to path for direct execution
    _parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    from common.config_loader import get_config, ConfigLoader
    from common.type_mapping import get_comfyui_output_type, validate_output_type, get_standardized_output_name
    from common.utils import is_type
    from common.schema_utils import get_input_type_from_config

# Constants for type mapping
DEFAULT_STEP = 0.01
DEFAULT_ROUND = 0.001

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".webm", ".mov", ".mpg", ".mpeg")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".mpga", ".m4a")

TYPE_MAPPING = {
    "string": "STRING",
    "integer": "INT",
    "number": "FLOAT",
    "boolean": "BOOLEAN",
}



def get_model_config_override(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        model_id: Model identifier (e.g., "renderartist/Technically-Color-Z-Image-Turbo")
        
    Returns:
        Model configuration dictionary or None
    """
    config = get_config()
    return config.get_model_config("huggingface", model_id)



def get_output_name_with_alias(
    output_type: str,
    schema_output_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    example_url: Optional[str] = None
) -> str:
    """
    Get the output name, using alias from config if available.
    
    Priority:
    1. Per-model alias in supported_models.yaml
    2. Default alias from global_outputs.yaml
    3. Standardized name from type_mapping
    
    Args:
        output_type: ComfyUI output type (IMAGE, AUDIO, VIDEO, STRING)
        schema_output_name: Original schema output name
        model_config: Model-specific configuration
        example_url: Example URL for extension detection
        
    Returns:
        Output name to use
    """
    config = get_config()
    
    # Check per-model alias first
    if model_config:
        outputs = model_config.get('outputs', {})
        for out_name, out_config in outputs.items():
            if out_name.lower() == schema_output_name.lower():
                if 'alias' in out_config:
                    return out_config['alias']
    
    # Check global outputs.yaml for default alias
    alias = config.get_output_alias("huggingface", "", schema_output_name, output_type, example_url)
    if alias:
        return alias
    
    # Fall back to standardized name
    return get_standardized_output_name(output_type, schema_output_name)


def convert_to_comfyui_input_type(
    input_name: str,
    input_type: str,
    openapi_format: Optional[str] = None,
    default_value: Any = None,
    config_override: Optional[str] = None,
) -> str:
    """
    Convert input type to ComfyUI input type.
    
    Args:
        input_name: Name of the input field
        input_type: Input type (string, integer, number, boolean)
        openapi_format: Format hint (uri, etc.)
        default_value: Default value for the input
        config_override: Explicit type from configuration
        
    Returns:
        ComfyUI input type (STRING, INT, FLOAT, BOOLEAN, IMAGE, AUDIO, VIDEO)
    """
    # Use config override if available
    if config_override:
        return config_override
    
    # Get field patterns from global config
    config = get_config()
    input_mapping = config.get_input_mapping("huggingface")
    image_fields = input_mapping.get('image_fields', [])
    audio_fields = input_mapping.get('audio_fields', [])
    video_fields = input_mapping.get('video_fields', [])
    
    # Normalize input name for matching
    input_name_lower = input_name.lower()
    
    # Check for URI format strings
    if input_type == "string" and openapi_format == "uri":
        if default_value and isinstance(default_value, str):
            if is_type(default_value, IMAGE_EXTENSIONS):
                return "IMAGE"
            elif is_type(default_value, VIDEO_EXTENSIONS):
                return "VIDEO"
            elif is_type(default_value, AUDIO_EXTENSIONS):
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
    
    # Check name for media types
    if any(x in input_name_lower for x in ["image", "mask"]):
        return "IMAGE"
    elif "audio" in input_name_lower:
        return "AUDIO"
    elif "video" in input_name_lower:
        return "VIDEO"

    return TYPE_MAPPING.get(input_type, "STRING")


def name_and_version(schema: Dict) -> tuple:
    """
    Extract model name and node name from HuggingFace schema.
    
    Args:
        schema: HuggingFace model schema
        
    Returns:
        Tuple of (model_name, node_name)
    """
    # Try different schema formats
    model_id = schema.get("model_id", "")
    
    if not model_id:
        # Try owner/name format
        owner = schema.get("owner", "")
        name = schema.get("name", "")
        model_id = f"{owner}/{name}" if owner else name
    
    # Get version if available
    version = schema.get("version", "latest")
    
    hf_model = model_id
    node_name = f"HF {model_id}"
    
    return hf_model, node_name


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


def get_parameter_order(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    schema_order: Optional[int] = None
) -> int:
    """
    Get sort order for a parameter.
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration
        schema_order: x-order from schema
        
    Returns:
        Sort order (lower = earlier in list)
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'order' in param_config:
            return param_config['order']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'order' in input_config:
            return input_config['order']
    
    if schema_order is not None:
        return schema_order
    
    return 100


def get_parameter_group(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get parameter group (system, basic, advanced).
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration
        
    Returns:
        Group name (default: "basic")
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'group' in param_config:
            return param_config['group']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'group' in input_config:
            return input_config['group']
    
    return "basic"


def sort_inputs_by_group_and_order(
    inputs: Dict[str, Any],
    model_config: Optional[Dict[str, Any]] = None,
    schema_order_map: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Sort inputs by group then by order.
    
    Group order: system (0), basic (1+), advanced (10+)
    
    Args:
        inputs: Dictionary of input definitions
        model_config: Model-specific configuration
        schema_order_map: Map of field names to x-order from schema
        
    Returns:
        Sorted dictionary
    """
    # Define group priority (lower = appears first)
    group_priority = {
        "system": 0,
        "basic": 1,
        "advanced": 2,
    }
    
    def get_sort_key(item):
        name, _ = item
        group = get_parameter_group(name, model_config)
        order = get_parameter_order(name, model_config, schema_order_map.get(name))
        group_ord = group_priority.get(group, 99)
        return (group_ord, order, name)
    
    sorted_items = sorted(inputs.items(), key=get_sort_key)
    return dict(sorted_items)


def schema_to_comfyui_input_types(schema: Dict) -> Dict[str, Any]:
    """
    Convert a HuggingFace schema to ComfyUI INPUT_TYPES format.
    
    For HuggingFace, we define inputs based on common inference parameters
    and model-specific configurations.
    
    Note: HuggingFace models execute locally and don't use dry_run/force_rerun.
    
    Args:
        schema: HuggingFace model schema
        
    Returns:
        Dictionary with 'required' and 'optional' input definitions
    """
    model_id, _ = name_and_version(schema)
    model_config = get_model_config_override(model_id)
    
    required_inputs = {}
    optional_inputs = {}
    
    # Process defined inputs
    inputs_config = schema.get("inputs", [])
    parameters = schema.get("parameters", {})
    
    # Collect schema order for fallback
    schema_order_map = {}
    
    # Add model name as required
    required_inputs["model"] = ("STRING", {"default": model_id})
    
    # Process defined inputs
    for idx, input_def in enumerate(inputs_config):
        input_name = input_def.get("name", "")
        input_type = input_def.get("type", "string")
        is_required = input_def.get("required", False)
        default_value = input_def.get("default")
        
        # Track schema order
        if "x-order" in input_def:
            schema_order_map[input_name] = input_def["x-order"]
        else:
            schema_order_map[input_name] = idx
        
        # Get explicit type override from config
        config_override = get_input_type_from_config(input_name, model_config)
        
        comfyui_type = convert_to_comfyui_input_type(
            input_name,
            input_type,
            input_def.get("format"),
            default_value,
            config_override
        )
        
        # Build input definition
        input_def_list = [comfyui_type]
        
        if "enum" in input_def:
            input_def_list[0] = input_def["enum"]
            if default_value is None and input_def_list[0]:
                default_value = input_def_list[0][0]
        
        input_options = {}
        if default_value is not None:
            input_options["default"] = default_value
        
        if "description" in input_def:
            input_options["description"] = input_def["description"]
        
        # Add numeric constraints
        if "min" in input_def:
            input_options["min"] = input_def["min"]
        if "max" in input_def:
            input_options["max"] = input_def["max"]
        
        if input_def_list[0] == "FLOAT":
            input_options["step"] = input_options.get("step", DEFAULT_STEP)
            input_options["round"] = input_options.get("round", DEFAULT_ROUND)
        
        input_def_list.append(input_options)
        
        input_tuple = tuple(input_def_list) if len(input_def_list) > 1 else input_def_list[0]
        
        if is_required:
            required_inputs[input_name] = input_tuple
        else:
            optional_inputs[input_name] = input_tuple
    
    # Add standard parameters from model config
    if model_config:
        params = model_config.get('parameters', {})
        for param_name, param_config in params.items():
            param_type = param_config.get('type', 'STRING')
            param_default = param_config.get('default', '')
            param_desc = param_config.get('description', '')
            
            input_tuple = (param_type, {"default": param_default, "description": param_desc})
            optional_inputs[param_name] = input_tuple
    
    # Add standard inference parameters if defined in schema
    if "max_new_tokens" in parameters:
        optional_inputs["max_new_tokens"] = (
            "INT",
            {"default": parameters["max_new_tokens"].get("default", 512), "min": 1, "max": 4096}
        )
    
    if "temperature" in parameters:
        optional_inputs["temperature"] = (
            "FLOAT",
            {"default": parameters["temperature"].get("default", 0.7), "min": 0.0, "max": 2.0}
        )
    
    if "top_p" in parameters:
        optional_inputs["top_p"] = (
            "FLOAT",
            {"default": parameters["top_p"].get("default", 0.9), "min": 0.0, "max": 1.0}
        )
    
    # Note: HuggingFace models don't use dry_run/force_rerun
    # They execute locally in ComfyUI immediately
    
    # Sort inputs by group and order
    required_sorted = sort_inputs_by_group_and_order(required_inputs, model_config, schema_order_map)
    optional_sorted = sort_inputs_by_group_and_order(optional_inputs, model_config, schema_order_map)
    
    result = {}
    if required_sorted:
        result["required"] = required_sorted
    if optional_sorted:
        result["optional"] = optional_sorted
    
    return result


def get_return_type(schema: Dict) -> Any:
    """
    Extract return type from schema.
    
    Now uses standardized type mapping from common.type_mapping module
    to ensure all output types match supported ComfyUI types.
    Output names are also standardized based on their type.
    
    Priority order:
    1. Explicit output config from supported_models.yaml (matches schema name) - HIGHEST PRIORITY
    2. Inferred from schema outputs
    
    Args:
        schema: HuggingFace model schema
        
    Returns:
        Dictionary mapping standardized output names to ComfyUI types
    """
    model_id, _ = name_and_version(schema)
    model_config = get_model_config_override(model_id)
    
    return_type = {}
    
    # Get output names from schema (case-insensitive for matching)
    schema_outputs = schema.get("outputs", [])
    schema_output_names = [o.get("name", "") for o in schema_outputs]
    
    # PRIORITY 1: Check for explicit output configuration from supported_models.yaml
    # This MUST take precedence over schema inference
    if model_config:
        outputs_config = model_config.get('outputs', {})
        
        # Create case-insensitive lookup for outputs config
        outputs_config_lower = {k.lower(): (k, v) for k, v in outputs_config.items()}
        
        config_matched = False
        for schema_output_name in schema_output_names:
            if not schema_output_name:
                continue
            config_key_lower = schema_output_name.lower()
            if config_key_lower in outputs_config_lower:
                # Found matching config using schema name - USE THIS!
                config_matched = True
                _, output_def = outputs_config_lower[config_key_lower]
                output_type = output_def.get('type', 'STRING')
                # Use standardized type mapping
                comfyui_type = get_comfyui_output_type(output_type, schema_output_name)
                # Validate the type is supported
                if validate_output_type(comfyui_type):
                    # Use output name with alias support
                    output_name = get_output_name_with_alias(comfyui_type, schema_output_name, model_config)
                    return_type[output_name] = comfyui_type
                else:
                    # Fall back to STRING if invalid
                    output_name = get_output_name_with_alias("STRING", schema_output_name, model_config)
                    return_type[output_name] = "STRING"
        
        # If we matched config, we're done - skip schema inference
        if config_matched:
            return return_type if return_type else {"text": "STRING"}
    
    # PRIORITY 2: Infer from schema outputs
    for output_def in schema_outputs:
        output_name = output_def.get("name", "output")
        output_type = output_def.get("type", "string")
        
        # Use standardized type mapping
        comfyui_type = get_comfyui_output_type(output_type, output_name)
        # Use output name with alias support
        final_output_name = get_output_name_with_alias(comfyui_type, output_name, model_config)
        return_type[final_output_name] = comfyui_type
    
    if not return_type:
        # Default: use standardized name "text" for STRING
        return_type = {"text": "STRING"}
    
    return return_type
