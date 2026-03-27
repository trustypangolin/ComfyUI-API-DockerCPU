"""
Parameter handling utilities for ComfyUI-API-DockerCPU

Provides functions for:
- Getting parameter options (multiline, etc.) from global_parameters.yaml
- Extracting ComfyUI input options for different parameter types
"""

from typing import Dict, Any, Optional


# Provider name to config key mapping
PROVIDER_KEY_MAP = {
    'replicate': 'replicate_api',
    'falai': 'fal_ai_api',
    'huggingface': 'huggingface_api',
}


def get_parameter_options(
    provider: str,
    param_name: str,
    comfyui_type: str,
) -> Dict[str, Any]:
    """
    Get options for a parameter from global_parameters.yaml.
    
    Args:
        provider: API provider name ("replicate", "falai", "huggingface")
        param_name: Parameter name (e.g., "prompt", "seed")
        comfyui_type: ComfyUI type (STRING, INT, FLOAT, etc.)
        
    Returns:
        Dictionary of options to add to input definition (e.g., {"multiline": True})
        
    Examples:
        >>> opts = get_parameter_options("falai", "prompt", "STRING")
        >>> opts.get("multiline")
        True
    """
    from common.config_loader import get_config
    
    config = get_config()
    
    # Get provider's section from global_parameters.yaml
    provider_key = PROVIDER_KEY_MAP.get(provider.lower(), provider.lower())
    provider_params = config.get_parameter_patterns(provider_key)
    
    # Get parameter-specific config
    params = provider_params.get('parameters', {})
    param_config = params.get(param_name, {})
    
    options = {}
    
    # For STRING types, check for multiline option
    if comfyui_type == "STRING":
        if param_config.get('multiline', False):
            options['multiline'] = True
    
    return options


def get_string_input_options(
    provider: str,
    param_name: str,
) -> Dict[str, Any]:
    """
    Get STRING input options for a parameter.
    
    Args:
        provider: API provider name
        param_name: Parameter name
        
    Returns:
        Dictionary with STRING input options (multiline, etc.)
    """
    return get_parameter_options(provider, param_name, "STRING")
