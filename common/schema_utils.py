"""
Schema conversion utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Schema type conversion
- Parameter ordering and grouping
- Model configuration handling
- Output name aliasing
"""

from typing import Dict, Any, Optional, List


def get_input_type_from_config(
    field_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Get explicit input type from model configuration.
    
    Args:
        field_name: Name of the input field
        model_config: Model-specific configuration (from supported_models.yaml)
        
    Returns:
        ComfyUI input type (STRING, INT, FLOAT, BOOLEAN, IMAGE, AUDIO, VIDEO)
        or None if not specified in config
        
    Examples:
        >>> config = {"inputs": {"image": {"type": "IMAGE"}}}
        >>> get_input_type_from_config("image", config)
        'IMAGE'
        >>> get_input_type_from_config("prompt", config)
        None
    """
    if not model_config:
        return None
    
    inputs = model_config.get('inputs', {})
    field_config = inputs.get(field_name, {})
    
    return field_config.get('type')


def get_standard_parameters(api_name: str) -> Dict[str, Any]:
    """
    Get standard parameters for nodes.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        
    Returns:
        Dictionary of standard parameter definitions from global_parameters.yaml
        
    Examples:
        >>> params = get_standard_parameters("falai")
        >>> "seed" in params
        True
        >>> "steps" in params
        True
    """
    from common.config_loader import get_config
    
    config = get_config()
    return config.get_standard_parameters(api_name)


def get_standard_parameters(api_name: str) -> Dict[str, Any]:
    """
    Get standard parameters for nodes.
    
    Args:
        api_name: API provider name ("falai", "huggingface", "replicate")
        
    Returns:
        Dictionary of standard parameter definitions from global_parameters.yaml
        
    Examples:
        >>> params = get_standard_parameters("falai")
        >>> "seed" in params
        True
        >>> "steps" in params
        True
    """
    from common.config_loader import get_config
    
    config = get_config()
    return config.get_standard_parameters(api_name)
