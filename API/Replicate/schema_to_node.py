"""
Schema to Node converter for Replicate API

Translates Replicate's OpenAPI schemas into ComfyUI INPUT_TYPES format.
Now uses YAML configuration for model-specific settings, parameter grouping,
and input/output type overrides.
"""

import json
import os
import re
import sys
from typing import Dict, Any, Optional, List

# Import the configuration loader - use absolute import with sys.path fallback
# This handles both installed package and direct execution scenarios
try:
    from common.config_loader import get_config, ConfigLoader
    from common.type_mapping import get_comfyui_output_type, validate_output_type, get_standardized_output_name
    from common.utils import is_type
    from common.schema_utils import get_input_type_from_config, get_standard_parameters
    from common.parameter_handlers import get_parameter_options
except ImportError:
    # Add parent directory to path for direct execution
    _parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    from common.config_loader import get_config, ConfigLoader
    from common.type_mapping import get_comfyui_output_type, validate_output_type, get_standardized_output_name
    from common.utils import is_type
    from common.schema_utils import get_input_type_from_config, get_standard_parameters
    from common.parameter_handlers import get_parameter_options

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

# Debug mode - enabled via DEBUG_API_TRUSTYPANGOLIN environment variable
DEBUG_MODE = os.environ.get("DEBUG_API_TRUSTYPANGOLIN", "false").lower() == "true"


def get_input_name_with_alias(
    input_name: str,
    input_type: str,
    is_array: bool = False,
    array_index: int = 1,
    model_config: Optional[Dict] = None
) -> str:
    """
    Get the input name, using alias from config if available.
    
    Args:
        input_name: Original schema field name
        input_type: ComfyUI type (IMAGE, AUDIO, VIDEO)
        is_array: Whether this is an array input
        array_index: Index for array inputs (1-based)
        model_config: Optional model config override
        
    Returns:
        Alias name if available, otherwise original name
    """
    config = get_config()
    
    # Check for per-model alias override
    if model_config:
        inputs_config = model_config.get('inputs', {})
        for config_name, config_def in inputs_config.items():
            if isinstance(config_def, dict) and config_name.lower() == input_name.lower():
                if 'alias' in config_def:
                    alias = config_def['alias']
                    if is_array:
                        suffix = config_def.get('alias_array_suffix', '_1')
                        return alias + suffix.replace('_1', f'_{array_index}')
                    return alias
    
    # Check global inputs.yaml for alias
    alias = config.get_input_alias("replicate", input_name, input_type, is_array, array_index)
    if alias:
        return alias
    
    # Return original name if no alias found
    return input_name


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



def get_max_images(model_name: str) -> int:
    """
    Get the max_images setting for a model from configuration.
    
    Args:
        model_name: Full model name with version (e.g., "owner/name:version")
        
    Returns:
        Maximum number of images supported (0 = optional, single image)
    """
    config = get_config()
    
    # Extract model name without version hash
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_max_images("replicate", model_base)


def get_array_input_mapping(model_name: str) -> Optional[str]:
    """
    Get the array input field name for a model from configuration.
    
    Args:
        model_name: Full model name with version
        
    Returns:
        Array input field name (e.g., "images") or None
    """
    config = get_config()
    
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_array_input_field("replicate", model_base)


def get_model_config_override(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get model-specific configuration overrides.
    
    Args:
        model_name: Full model name with version
        
    Returns:
        Model configuration dictionary or None
    """
    config = get_config()
    
    model_base = model_name.split(":")[0] if ":" in model_name else model_name
    
    return config.get_model_config("replicate", model_base)


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
    alias = config.get_output_alias("replicate", "", schema_output_name, output_type, example_url)
    if alias:
        return alias
    
    # Fall back to standardized name
    return get_standardized_output_name(output_type, schema_output_name)



def get_array_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get array configuration for an input field.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration
        
    Returns:
        Dictionary with 'is_array', 'max_items', 'is_optional' or empty dict
    """
    if not model_config:
        return {}
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return {
        'is_array': field_config.get('is_array', False),
        'max_items': field_config.get('max_items'),
        'is_optional': field_config.get('is_optional', False),
    }


def convert_to_comfyui_input_type(
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
        input_name: Name of the input field
        openapi_type: OpenAPI type (string, integer, number, boolean, array)
        openapi_format: OpenAPI format (uri, etc.)
        default_example_input: Example input from schema
        items_type: Type of array items
        items_format: Format of array items
        config_override: Explicit type from configuration
        
    Returns:
        ComfyUI input type (STRING, INT, FLOAT, BOOLEAN, IMAGE, AUDIO, VIDEO)
    """
    # Use config override if available
    if config_override:
        return config_override
    
    # Get field patterns from global config
    config = get_config()
    input_mapping = config.get_input_mapping("replicate")
    image_fields = input_mapping.get('image_fields', [])
    audio_fields = input_mapping.get('audio_fields', [])
    video_fields = input_mapping.get('video_fields', [])
    
    # Normalize input name for matching
    input_name_lower = input_name.lower()
    
    # Check if field matches image patterns
    if openapi_type == "string" and openapi_format == "uri":
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

    return TYPE_MAPPING.get(openapi_type, "STRING")


def name_and_version(schema: Dict) -> tuple:
    """
    Extract model name and node name from schema.
    
    Args:
        schema: Replicate OpenAPI schema
        
    Returns:
        Tuple of (replicate_model, node_name)
    """
    author = schema["owner"]
    name = schema["name"]
    version = schema["latest_version"]["id"]
    replicate_model = f"{author}/{name}:{version}"
    node_name = f"Replicate {author}/{name}"
    return replicate_model, node_name


def debug_schema_conversion(schema: Dict, input_types: Dict, return_types: Dict):
    """
    Debug helper to print INPUT_TYPES and RETURN_TYPES.
    
    Args:
        schema: The source schema
        input_types: Generated INPUT_TYPES
        return_types: Generated RETURN_TYPES
    """
    if not DEBUG_MODE:
        return
    
    replicate_model, node_name = name_and_version(schema)
    
    print(f"\n{'='*60}")
    print(f"[DEBUG] Schema Conversion for: {replicate_model}")
    print(f"{'='*60}")
    
    # Get field patterns from global config
    config = get_config()
    input_mapping = config.get_input_mapping("replicate")
    image_fields = [f.lower() for f in input_mapping.get('image_fields', [])]
    audio_fields = [f.lower() for f in input_mapping.get('audio_fields', [])]
    video_fields = [f.lower() for f in input_mapping.get('video_fields', [])]
    
    print(f"\nINPUT (from global_inputs.yaml):")
    inputs_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            name_lower = name.lower()
            # Check if this is a media input (IMAGE, AUDIO, VIDEO)
            is_media = False
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name in ('IMAGE', 'AUDIO', 'VIDEO'):
                    is_media = True
                    inputs_found.append(f"  [I] {name}: {type_name}")
            
            # Also check by field name patterns
            if not is_media:
                if any(p in name_lower for p in image_fields) or any(p in name_lower for p in audio_fields) or any(p in name_lower for p in video_fields):
                    if isinstance(definition, tuple):
                        type_name = definition[0] if isinstance(definition[0], str) else "COMBO"
                        inputs_found.append(f"  [I] {name}: {type_name}")
            
            # Check for IMAGE array slots
            if not is_media and (name_lower.startswith('image') or 'image' in name_lower):
                if isinstance(definition, tuple) and len(definition) >= 2:
                    opts = definition[1] if isinstance(definition[1], dict) else {}
                    if opts.get('maxLen') == 1:
                        inputs_found.append(f"  [I] {name}: IMAGE")
    
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            name_lower = name.lower()
            # Check if this is a media input (IMAGE, AUDIO, VIDEO)
            is_media = False
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name in ('IMAGE', 'AUDIO', 'VIDEO'):
                    is_media = True
                    inputs_found.append(f"  [I] {name}: {type_name}")
            
            # Also check by field name patterns
            if not is_media:
                if any(p in name_lower for p in image_fields) or any(p in name_lower for p in audio_fields) or any(p in name_lower for p in video_fields):
                    if isinstance(definition, tuple):
                        type_name = definition[0] if isinstance(definition[0], str) else "COMBO"
                        inputs_found.append(f"  [I] {name}: {type_name}")
            
            # Check for IMAGE array slots
            if not is_media and (name_lower.startswith('image') or 'image' in name_lower):
                if isinstance(definition, tuple) and len(definition) >= 2:
                    opts = definition[1] if isinstance(definition[1], dict) else {}
                    if opts.get('maxLen') == 1:
                        inputs_found.append(f"  [I] {name}: IMAGE")
    
    if inputs_found:
        for line in inputs_found:
            print(line)
    else:
        print("  (none)")
    
    print(f"\nPARAMETERS (from global_parameters.yaml):")
    params_found = []
    if 'required' in input_types:
        for name, definition in input_types['required'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if 'optional' in input_types:
        for name, definition in input_types['optional'].items():
            if isinstance(definition, tuple) and len(definition) >= 1:
                type_name = definition[0]
                if isinstance(type_name, str) and type_name not in ('IMAGE', 'AUDIO', 'VIDEO'):
                    params_found.append(f"  [P] {name}: {type_name}")
            elif isinstance(definition, str) and definition not in ('IMAGE', 'AUDIO', 'VIDEO'):
                params_found.append(f"  [P] {name}: {definition}")
    
    if params_found:
        for line in params_found:
            print(line)
    else:
        print("  (none)")
    
    print(f"\nOUTPUT: (from global_outputs.yaml):")
    if return_types:
        for name, type_name in return_types.items():
            print(f"  [O] {name}: {type_name}")
    elif input_types:
        print("  (not yet determined - see RETURN_TYPES debug)")
        # Print the raw return_types for debugging
        print(f"  Raw return_types passed: {return_types}")
    else:
        print("  (none)")
    
    print(f"{'='*60}\n")


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

    # Handle allOf containing $ref
    if "allOf" in prop_data and isinstance(prop_data["allOf"], list):
        resolved = {}
        for item in prop_data["allOf"]:
            if "$ref" in item:
                ref_path = item["$ref"].split("/")
                current = openapi_schema
                for path in ref_path[1:]:
                    if path not in current:
                        break
                    current = current[path]
                else:
                    if DEBUG_MODE:
                        print(f"[DEBUG] resolve_schema: resolved allOf $ref '{item['$ref']}' -> keys: {list(current.keys())}")
                    resolved.update(current)
                    continue
                break
            else:
                resolved.update(item)
        # Merge remaining non-allOf properties from original
        for key, value in prop_data.items():
            if key != "allOf":
                resolved[key] = value
        if DEBUG_MODE:
            print(f"[DEBUG] resolve_schema: allOf result keys: {list(resolved.keys())}, has enum: {'enum' in resolved}")
        return resolved

    return prop_data


def get_default_example_input(schema: Dict) -> Optional[Dict]:
    """Extract default example input from schema."""
    return schema.get("default_example_input", {})


def inputs_that_need_arrays(schema: Dict) -> list:
    """
    Find inputs that need array processing.
    
    Args:
        schema: Replicate OpenAPI schema
        
    Returns:
        List of input names that should be treated as arrays
    """
    array_inputs = []
    
    # Get components from the nested openapi_schema location
    openapi_schema = schema.get("latest_version", {}).get("openapi_schema", {})
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    
    for schema_name, schema_data in schemas.items():
        props = schema_data.get("properties", {})
        for prop_name, prop_data in props.items():
            resolved = resolve_schema(prop_data, openapi_schema)
            if resolved.get("type") == "array":
                array_inputs.append(prop_name)
    
    return array_inputs


def get_parameter_order(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    schema_order: Optional[int] = None
) -> int:
    """
    Get sort order for a parameter.
    
    Order priority:
    1. Explicit order from config (-1 for system, 0+ for user params)
    2. Schema x-order if available
    3. Default order (100)
    
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
    
    Group order: system (-2, -1), basic (0+), advanced (10+)
    
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
    Convert a Replicate OpenAPI schema to ComfyUI INPUT_TYPES format.
    
    Supports:
    - Parameter grouping (system, basic, advanced)
    - Custom parameter ordering
    - Explicit input type overrides from config
    - Standard parameters (force_rerun)
    
    Args:
        schema: Replicate OpenAPI schema
        
    Returns:
        Dictionary with 'required' and 'optional' input definitions
    """
    replicate_model, _ = name_and_version(schema)
    model_config = get_model_config_override(replicate_model)
    
    default_example_input = get_default_example_input(schema)
    
    # Collect x-order from schema for fallback ordering
    schema_order_map = {}
    
    # Process inputs into groups - separate required and optional
    system_inputs_required = {}
    basic_inputs_required = {}
    advanced_inputs_required = {}
    system_inputs_optional = {}
    basic_inputs_optional = {}
    advanced_inputs_optional = {}
    
    # Get components from the nested openapi_schema location
    # The schema structure has: schema -> latest_version -> openapi_schema -> components
    openapi_schema = schema.get("latest_version", {}).get("openapi_schema", {})
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    
    # Only process the Input schema (not all schemas like Output, Status, etc.)
    input_schema = schemas.get("Input", {})
    props = input_schema.get("properties", {})
    input_required = input_schema.get("required", [])
    
    for prop_name, prop_data in props.items():
        resolved = resolve_schema(prop_data, openapi_schema)
        openapi_type = resolved.get("type", "string")
        openapi_format = resolved.get("format")
        
        # Get x-order from schema for ordering
        if "x-order" in resolved:
            schema_order_map[prop_name] = resolved["x-order"]
        
        # Handle array types
        items = resolved.get("items", {})
        items_type = items.get("type")
        items_format = items.get("format")
        
        # Get explicit type override from config
        config_override = get_input_type_from_config(prop_name, model_config)
        
        # Determine ComfyUI type
        comfyui_type = convert_to_comfyui_input_type(
            prop_name,
            openapi_type,
            openapi_format,
            default_example_input,
            items_type,
            items_format,
            config_override
        )
        
        # Get default value
        default_value = None
        if "default" in resolved:
            default_value = resolved["default"]
        elif comfyui_type == "INT":
            default_value = 0
        elif comfyui_type == "FLOAT":
            default_value = 0.0
        elif comfyui_type == "BOOLEAN":
            default_value = False
        elif comfyui_type == "STRING":
            default_value = ""
        
        # Check if required
        is_required = prop_name in input_required
        
        # Build input definition
        input_def = [comfyui_type]
        
        if openapi_type == "string" and "enum" in resolved:
            # Enum values
            input_def[0] = resolved["enum"]
            if default_value is None and input_def[0]:
                default_value = input_def[0][0]
            if DEBUG_MODE:
                print(f"[DEBUG] ENUM detected for '{prop_name}': {resolved.get('enum')}")
        elif DEBUG_MODE and openapi_type == "string":
            print(f"[DEBUG] STRING (no enum) for '{prop_name}': type={openapi_type}, keys={list(resolved.keys())}")
        
        input_options = {}
        if default_value is not None:
            input_options["default"] = default_value
        
        if "description" in resolved:
            input_options["description"] = resolved["description"]
        
        # Add numeric constraints
        if "minimum" in resolved or "maximum" in resolved:
            if "minimum" in resolved:
                input_options["min"] = resolved["minimum"]
            if "maximum" in resolved:
                input_options["max"] = resolved["maximum"]
        
        # Add maxItems constraint for array types (from description)
        if openapi_type == "array":
            description = resolved.get("description", "")
            max_items = extract_max_items_from_description(description)
            if max_items:
                input_options["max"] = max_items
        
        if input_def[0] == "FLOAT" and "step" not in input_options:
            input_options["step"] = DEFAULT_STEP
            input_options["round"] = DEFAULT_ROUND
        
        # Add parameter options from global_parameters.yaml (e.g., multiline for prompts)
        param_options = get_parameter_options("replicate", prop_name, comfyui_type)
        input_options.update(param_options)
        
        input_def.append(input_options)
        
        input_tuple = tuple(input_def) if len(input_def) > 1 else input_def[0]
        
        # Check if this should be expanded into multiple slots (array input)
        array_config = get_array_config(prop_name, model_config)
        is_array = array_config.get('is_array', False)
        
        # Also check if it's an array type with max items
        if openapi_type == "array" and not is_array:
            description = resolved.get("description", "")
            max_items = extract_max_items_from_description(description)
            if max_items:
                is_array = True
                if not array_config.get('max_items'):
                    array_config['max_items'] = max_items
        
        # Determine group and add to appropriate dict
        group = get_parameter_group(prop_name, model_config)
        
        # Get target dicts based on group AND required/optional status
        required_dicts = {
            "system": system_inputs_required,
            "basic": basic_inputs_required,
            "advanced": advanced_inputs_required,
        }
        optional_dicts = {
            "system": system_inputs_optional,
            "basic": basic_inputs_optional,
            "advanced": advanced_inputs_optional,
        }
        
        # Handle array inputs by expanding into multiple slots
        if is_array:
            # Get max_count from config, description, or default to 5
            max_count = array_config.get('max_items')
            if not max_count:
                # Check model-level max_images config
                if model_config:
                    max_count = model_config.get('max_images')
            if not max_count:
                description = resolved.get("description", "")
                max_count = extract_max_items_from_description(description)
            if not max_count:
                max_count = 5  # Default to 5 slots for array inputs without explicit max
            
            # Create individual slots: IMAGE, IMAGE_1, IMAGE_2, ..., IMAGE_N
            base_order = schema_order_map.get(prop_name, 0)
            for i in range(1, max_count + 1):
                # Use alias for slot name (e.g., IMAGE, IMAGE_1, IMAGE_2, ...)
                slot_name = get_input_name_with_alias(
                    prop_name, 
                    "IMAGE", 
                    is_array=True, 
                    array_index=i,
                    model_config=model_config
                )
                # Each slot is a single image (IMAGE type with maxLen=1)
                slot_def = ("IMAGE", {"default": None, "maxLen": 1})
                # First slot follows required/optional from schema, rest are optional
                if i == 1:
                    # First slot follows the required status of the original field
                    if is_required:
                        required_dicts[group][slot_name] = slot_def
                    else:
                        optional_dicts[group][slot_name] = slot_def
                else:
                    # Additional slots are always optional
                    optional_dicts[group][slot_name] = slot_def
                # Update schema_order_map for proper ordering
                schema_order_map[slot_name] = base_order + (i - 1) * 0.01
        else:
            # Non-array inputs - use alias if available
            is_media = comfyui_type in ("IMAGE", "AUDIO", "VIDEO")
            if is_media:
                input_name_with_alias = get_input_name_with_alias(
                    prop_name,
                    comfyui_type,
                    is_array=False,
                    array_index=1,
                    model_config=model_config
                )
            else:
                input_name_with_alias = prop_name
            
            if is_required:
                required_dicts[group][input_name_with_alias] = input_tuple
            else:
                optional_dicts[group][input_name_with_alias] = input_tuple
    
    # Sort each group for required
    system_sorted = sort_inputs_by_group_and_order(system_inputs_required, model_config, schema_order_map)
    basic_sorted = sort_inputs_by_group_and_order(basic_inputs_required, model_config, schema_order_map)
    advanced_sorted = sort_inputs_by_group_and_order(advanced_inputs_required, model_config, schema_order_map)
    
    # Combine required: system first, then basic, then advanced
    final_required = {}
    final_required.update(system_sorted)
    final_required.update(basic_sorted)
    final_required.update(advanced_sorted)
    
    # Sort optional groups
    system_optional_sorted = sort_inputs_by_group_and_order(system_inputs_optional, model_config, schema_order_map)
    basic_optional_sorted = sort_inputs_by_group_and_order(basic_inputs_optional, model_config, schema_order_map)
    advanced_optional_sorted = sort_inputs_by_group_and_order(advanced_inputs_optional, model_config, schema_order_map)
    
    # Add standard parameters from config (always required/system)
    standard_params = get_standard_parameters("replicate")
    for param_name, param_def in standard_params.items():
        param_type = param_def.get('type', 'BOOLEAN')
        param_default = param_def.get('default', False)
        param_desc = param_def.get('description', '')
        param_group = param_def.get('group', 'system')
        param_order = param_def.get('order', -1)
        
        param_tuple = (param_type, {"default": param_default, "description": param_desc})
        
        if param_group == "system":
            system_sorted[param_name] = param_tuple
        elif param_group == "advanced":
            advanced_sorted[param_name] = param_tuple
        else:
            basic_sorted[param_name] = param_tuple
    
    # Rebuild with sorted groups for required
    final_required = {}
    final_required.update(sort_inputs_by_group_and_order(system_sorted, model_config, schema_order_map))
    final_required.update(sort_inputs_by_group_and_order(basic_sorted, model_config, schema_order_map))
    final_required.update(sort_inputs_by_group_and_order(advanced_sorted, model_config, schema_order_map))
    
    # Build optional dict
    final_optional = {}
    final_optional.update(system_optional_sorted)
    final_optional.update(basic_optional_sorted)
    final_optional.update(advanced_optional_sorted)
    
    result = {}
    if final_required:
        result["required"] = final_required
    if final_optional:
        result["optional"] = final_optional
    
    # Debug output
    debug_schema_conversion(schema, result, {})
    
    return result


def get_return_type(schema: Dict) -> Any:
    """
    Extract return type from schema.
    
    Now uses standardized type mapping from common.type_mapping module
    to ensure all output types match supported ComfyUI types.
    Output names are also standardized based on their type.
    
    Priority order:
    1. Explicit output config from supported_models.yaml (matches schema name) - HIGHEST PRIORITY
    2. Inferred from Output schema (type in schema)
    3. Inferred from example output (file extension detection)
    
    Args:
        schema: Replicate OpenAPI schema
        
    Returns:
        Dictionary mapping standardized output names to ComfyUI types
    """
    import sys
    replicate_model, _ = name_and_version(schema)
    model_config = get_model_config_override(replicate_model)
    
    return_type = {}
    
    # Get output schema names from the schema (case-insensitive for matching)
    schema_output_names = []
    openapi_schema = schema.get("latest_version", {}).get("openapi_schema", {})
    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    
    # Check for Output schema (case-insensitive)
    for schema_name in schemas.keys():
        if schema_name.lower() == "output":
            schema_output_names.append(schema_name)
    
    # Debug: trace what we found
    if DEBUG_MODE:
        print(f"[DEBUG] get_return_type: {replicate_model}", flush=True)
        print(f"  schema_output_names: {schema_output_names}", flush=True)
        print(f"  model_config has outputs: {'outputs' in model_config if model_config else False}", flush=True)
    
    # PRIORITY 1: Check for explicit output configuration from supported_models.yaml
    # This MUST take precedence over schema inference
    if model_config:
        outputs_config = model_config.get('outputs', {})
        
        # Create case-insensitive lookup for outputs config
        outputs_config_lower = {k.lower(): (k, v) for k, v in outputs_config.items()}
        
        config_matched = False
        for schema_output_name in schema_output_names:
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
    
    # PRIORITY 2: Infer from Output schema (type in schema)
    if schema_output_names:
        output_schema_name = schema_output_names[0]
        output_schema = schemas.get(output_schema_name, {})
        output_type = output_schema.get("type", "string")
        output_format = output_schema.get("format", "")
        
        # For arrays, check items.format instead of output_format
        # Some schemas have: {"type": "array", "items": {"type": "string", "format": "uri"}}
        items_format = ""
        if output_type == "array":
            items_format = output_schema.get("items", {}).get("format", "")
            if DEBUG_MODE:
                print(f"  output_type is array, items_format: {items_format}", flush=True)
        
        if DEBUG_MODE:
            print(f"  output_schema_name: {output_schema_name}", flush=True)
            print(f"  output_type: {output_type}", flush=True)
            print(f"  output_format: {output_format}", flush=True)
        
        # Use type from schema, but detect image/audio/video from format
        # Check both output_format (for non-array types) and items_format (for arrays)
        effective_format = output_format if output_format else items_format
        if effective_format in ("uri", "url"):
            # Check example output for file extension
            # Note: Replicate uses "default_example" not "default_example_output"
            default_example = schema.get("default_example", {})
            if DEBUG_MODE:
                print(f"  default_example: {default_example}", flush=True)
            if isinstance(default_example, dict):
                # The output is directly in default_example.output
                output_value = default_example.get("output")
                if isinstance(output_value, str):
                    # Single URL value
                    comfyui_type = get_comfyui_output_type("string", output_schema_name, output_value)
                    if DEBUG_MODE:
                        print(f"  Detected type from URL: {comfyui_type} (file: {output_value})", flush=True)
                    output_name = get_output_name_with_alias(comfyui_type, output_schema_name, model_config, output_value)
                    return_type[output_name] = comfyui_type
                    return return_type
                elif isinstance(output_value, list) and output_value:
                    # Array of URLs - check first item
                    first_item = output_value[0]
                    if isinstance(first_item, str):
                        comfyui_type = get_comfyui_output_type("string", output_schema_name, first_item)
                        if DEBUG_MODE:
                            print(f"  Detected type from array URL: {comfyui_type} (file: {first_item})", flush=True)
                        output_name = get_output_name_with_alias(comfyui_type, output_schema_name, model_config, first_item)
                        return_type[output_name] = comfyui_type
                        return return_type
        
        # Default to STRING if no example output
        comfyui_type = get_comfyui_output_type(output_type, output_schema_name)
        if DEBUG_MODE:
            print(f"  Fallback type: {comfyui_type}", flush=True)
        output_name = get_output_name_with_alias(comfyui_type, output_schema_name, model_config)
        return_type[output_name] = comfyui_type
        return return_type if return_type else {"text": "STRING"}
    
    # PRIORITY 3: Infer from example output (file extension detection)
    default_example_output = schema.get("default_example_output", {})
    if isinstance(default_example_output, dict):
        for key, value in default_example_output.items():
            if isinstance(value, str):
                comfyui_type = get_comfyui_output_type("string", key, value)
                output_name = get_output_name_with_alias(comfyui_type, key, model_config, value)
                return_type[output_name] = comfyui_type
    
    if not return_type:
        # Default: use standardized name "text" for STRING
        return_type = {"text": "STRING"}
    
    # Debug output for RETURN_TYPES - shows what the schema_to_node generates
    if DEBUG_MODE:
        import sys
        print(f"\n{'='*60}", flush=True)
        print(f"[DEBUG] get_return_type() would return: {replicate_model}", flush=True)
        print(f"  Final return_type dict: {return_type}", flush=True)
        print(f"  RETURN_TYPES tuple: {tuple(return_type.values())}", flush=True)
        print(f"  RETURN_NAMES tuple: {tuple(return_type.keys())}", flush=True)
        for name, type_name in return_type.items():
            print(f"  [O] {name}: {type_name}", flush=True)
        print(f"{'='*60}\n", flush=True)
    
    return return_type
