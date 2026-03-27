"""
YAML Configuration Loader for ComfyUI-API-DockerCPU

Loads and provides access to:
- supported_models.yaml: Model-specific overrides
- global_inputs.yaml: INPUT field patterns (IMAGE, VIDEO, AUDIO)
- global_parameters.yaml: PARAMETER patterns (STRING, INT, FLOAT, COMBO, BOOLEAN)
- global_outputs.yaml: OUTPUT field patterns

This module separates INPUTS (media fields) from PARAMETERS (typed values).
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from functools import lru_cache

# Default configuration directory
CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration file paths
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "supported_models.yaml")
GLOBAL_INPUTS_PATH = os.path.join(CONFIG_DIR, "global_inputs.yaml")
GLOBAL_PARAMETERS_PATH = os.path.join(CONFIG_DIR, "global_parameters.yaml")
GLOBAL_OUTPUTS_PATH = os.path.join(CONFIG_DIR, "global_outputs.yaml")


class ConfigLoader:
    """
    Configuration loader with caching and validation.
    
    Loads four configuration files:
    1. supported_models.yaml - Model-specific overrides
    2. global_inputs.yaml - INPUT field patterns (IMAGE, VIDEO, AUDIO)
    3. global_parameters.yaml - PARAMETER patterns (STRING, INT, FLOAT, COMBO, BOOLEAN)
    4. global_outputs.yaml - OUTPUT field patterns
    """
    
    _instance = None
    _config = None
    _global_inputs = None
    _global_parameters = None
    _global_outputs = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Load all configuration files."""
        self._load_main_config()
        self._load_global_inputs()
        self._load_global_parameters()
        self._load_global_outputs()
    
    def _load_main_config(self, config_path: Optional[str] = None) -> None:
        """Load main configuration from YAML file."""
        path = config_path or DEFAULT_CONFIG_PATH
        
        if not os.path.exists(path):
            # Fallback to JSON if YAML doesn't exist
            json_path = path.replace('.yaml', '.json')
            if os.path.exists(json_path):
                self._load_json_fallback(json_path)
                return
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
    
    def _load_global_inputs(self) -> None:
        """Load global inputs configuration."""
        if os.path.exists(GLOBAL_INPUTS_PATH):
            with open(GLOBAL_INPUTS_PATH, 'r', encoding='utf-8') as f:
                self._global_inputs = yaml.safe_load(f) or {}
        else:
            self._global_inputs = {}
    
    def _load_global_parameters(self) -> None:
        """Load global parameters configuration."""
        if os.path.exists(GLOBAL_PARAMETERS_PATH):
            with open(GLOBAL_PARAMETERS_PATH, 'r', encoding='utf-8') as f:
                self._global_parameters = yaml.safe_load(f) or {}
        else:
            self._global_parameters = {}
    
    def _load_global_outputs(self) -> None:
        """Load global outputs configuration."""
        if os.path.exists(GLOBAL_OUTPUTS_PATH):
            with open(GLOBAL_OUTPUTS_PATH, 'r', encoding='utf-8') as f:
                self._global_outputs = yaml.safe_load(f) or {}
        else:
            self._global_outputs = {}
    
    def _load_json_fallback(self, json_path: str) -> None:
        """Load configuration from JSON file (for migration period)."""
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            self._config = json.load(f)
    
    def reload(self, config_path: Optional[str] = None) -> None:
        """Reload all configuration files."""
        self._config = None
        self._global_inputs = None
        self._global_parameters = None
        self._global_outputs = None
        # Load global configs first (they don't depend on main config)
        self._load_global_inputs()
        self._load_global_parameters()
        self._load_global_outputs()
        # Load main config once (uses config_path if provided, otherwise default path)
        self._load_main_config(config_path)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        if self._config is None:
            self._load_config()
        return self._config
    
    @property
    def defaults(self) -> Dict[str, Any]:
        """Get global default settings."""
        return self.config.get('defaults', {})
    
    @property
    def replicate(self) -> Dict[str, Any]:
        """Get Replicate provider configuration."""
        return self.config.get('replicate', {})
    
    @property
    def falai(self) -> Dict[str, Any]:
        """Get Fal.ai provider configuration."""
        return self.config.get('falai', {})
    
    @property
    def huggingface(self) -> Dict[str, Any]:
        """Get HuggingFace provider configuration."""
        return self.config.get('huggingface', {})
    
    @property
    def global_inputs(self) -> Dict[str, Any]:
        """Get global inputs configuration."""
        if self._global_inputs is None:
            self._load_global_inputs()
        return self._global_inputs
    
    @property
    def global_parameters(self) -> Dict[str, Any]:
        """Get global parameters configuration."""
        if self._global_parameters is None:
            self._load_global_parameters()
        return self._global_parameters
    
    @property
    def global_outputs(self) -> Dict[str, Any]:
        """Get global outputs configuration."""
        if self._global_outputs is None:
            self._load_global_outputs()
        return self._global_outputs
    
    def get_input_patterns(self, provider: str) -> Dict[str, Any]:
        """
        Get input field patterns for a provider.
        
        Args:
            provider: Provider name (replicate, falai, huggingface)
            
        Returns:
            Dictionary with input patterns (IMAGE, VIDEO, AUDIO fields)
        """
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_inputs = self.global_inputs.get(provider_key, {})
        return provider_inputs
    
    def get_parameter_patterns(self, provider: str) -> Dict[str, Any]:
        """
        Get parameter patterns for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with parameter patterns and standard parameters
        """
        provider_params = self.global_parameters.get(provider.lower(), {})
        return provider_params
    
    def get_output_patterns(self, provider: str) -> Dict[str, Any]:
        """
        Get output patterns for a provider from global_outputs.yaml.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary with output patterns and supported types
        """
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_outputs = self.global_outputs.get(provider_key, {})
        return provider_outputs
    
    def get_supported_output_types(self) -> List[str]:
        """
        Get list of supported ComfyUI output types.
        
        Returns:
            List of supported types (IMAGE, AUDIO, VIDEO, STRING, MASK)
        """
        return self.global_outputs.get('supported_types', [
            'IMAGE', 'AUDIO', 'VIDEO', 'STRING', 'MASK'
        ])
    
    def get_output_alias(
        self, 
        provider: str, 
        model_id: str, 
        output_name: str,
        output_type: Optional[str] = None,
        example_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the alias name for an output field.
        
        Priority:
        1. Per-model alias override in supported_models.yaml
        2. Default alias from global_outputs.yaml pattern match
        
        Args:
            provider: Provider name
            model_id: Model identifier
            output_name: Original output field name
            output_type: The detected ComfyUI output type (IMAGE, AUDIO, VIDEO, STRING)
            example_url: Example URL from the schema (for file extension detection)
            
        Returns:
            Alias name or None to use original name
        """
        # Check per-model override first
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            outputs = model_config.get('outputs', {})
            # Check if there's an alias for this output
            for out_name, out_config in outputs.items():
                if out_name.lower() == output_name.lower():
                    if 'alias' in out_config:
                        return out_config['alias']
        
        # Check global patterns for default alias
        output_patterns = self.get_output_patterns(provider)
        patterns = output_patterns.get('output_patterns', {})
        
        # For each pattern, check if it matches
        for pattern_name, pattern_config in patterns.items():
            if 'default_alias' not in pattern_config:
                continue
                
            # Check inferred_type matches the output_type
            inferred_type = pattern_config.get('inferred_type', '')
            if output_type and inferred_type and inferred_type != output_type:
                continue
            
            # For Replicate: Match by schema name "Output" and check example extensions
            # For FalAi: Match by field name (image, images, video, audio)
            schema_match = pattern_config.get('schema_match', {})
            field_match = pattern_config.get('field_match', {})
            
            # Check schema name match
            if schema_match:
                match_name = schema_match.get('name', '')
                if match_name.lower() == output_name.lower():
                    # Schema name matches, check example extensions
                    example_extensions = pattern_config.get('example_extensions', [])
                    if example_url and example_extensions:
                        url_lower = example_url.lower()
                        if any(url_lower.endswith(ext) for ext in example_extensions):
                            return pattern_config['default_alias']
                    elif not example_extensions:
                        # No extensions to check, use this pattern
                        return pattern_config['default_alias']
            
            # Check field name match (for FalAi-style configs)
            if field_match:
                match_name = field_match.get('name', '')
                if match_name.lower() == output_name.lower():
                    return pattern_config['default_alias']
        
        # Default aliases based on output type
        default_aliases = {
            'IMAGE': 'IMAGE',
            'IMAGES': 'IMAGES',
            'AUDIO': 'AUDIO',
            'VIDEO': 'VIDEO',
            'STRING': 'text',
        }
        
        if output_type:
            return default_aliases.get(output_type.upper(), None)
        
        return None
    
    def get_standard_parameters(self, provider: str) -> Dict[str, Any]:
        """
        Get standard parameters for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary of standard parameter definitions
        """
        provider_params = self.global_parameters.get(provider.lower(), {})
        return provider_params.get('standard_parameters', {})
    
    def get_model_config(
        self, 
        provider: str, 
        model_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific model.
        
        Args:
            provider: Provider name (replicate, falai, huggingface)
            model_id: Model identifier (owner/name format)
            
        Returns:
            Model configuration dictionary or None if not found
        """
        provider_config = self.config.get(provider.lower(), {})
        
        if provider.lower() == 'huggingface':
            repos = provider_config.get('repos', [])
            for repo in repos:
                if isinstance(repo, dict) and repo.get('id') == model_id:
                    return repo
                elif isinstance(repo, str) and repo == model_id:
                    return {'id': repo}
            return None
        
        models = provider_config.get('models', {})
        return models.get(model_id)
    
    def get_model_ids(self, provider: str) -> List[str]:
        """Get list of model IDs for a provider."""
        provider_config = self.config.get(provider.lower(), {})
        
        if provider.lower() == 'huggingface':
            repos = provider_config.get('repos', [])
            return [
                r if isinstance(r, str) else r.get('id', '')
                for r in repos
            ]
        
        models = provider_config.get('models', {})
        return list(models.keys())
    
    def get_standard_parameters(
        self, 
        provider: str,
        include_system: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get standard parameters for a provider from global_parameters.yaml.
        
        Args:
            provider: Provider name
            include_system: Include system parameters (dry_run, force_rerun)
            
        Returns:
            Dictionary of standard parameter definitions
        """
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_params = self.global_parameters.get(provider_key, {})
        standard_params = provider_params.get('standard_parameters', {})
        
        if not include_system:
            # Filter out system parameters
            standard_params = {
                k: v for k, v in standard_params.items()
                if v.get('group') != 'system'
            }
        
        return standard_params
    
    def get_input_mapping(self, provider: str) -> Dict[str, List[str]]:
        """
        Get input field name patterns for a provider from global_inputs.yaml.
        
        Returns:
            Dictionary with image_fields, audio_fields, video_fields
        """
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_inputs = self.global_inputs.get(provider_key, {})
        inputs_config = provider_inputs.get('inputs', {})
        
        # Extract fields by type
        image_fields = []
        audio_fields = []
        video_fields = []
        
        for input_name, input_config in inputs_config.items():
            comfyui_type = input_config.get('comfyui_type', '')
            field_match = input_config.get('field_match', {})
            name_patterns = field_match.get('name_patterns', [])
            
            if comfyui_type == 'IMAGE':
                image_fields.extend(name_patterns)
            elif comfyui_type == 'AUDIO':
                audio_fields.extend(name_patterns)
            elif comfyui_type == 'VIDEO':
                video_fields.extend(name_patterns)
        
        return {
            'image_fields': image_fields,
            'audio_fields': audio_fields,
            'video_fields': video_fields,
        }
    
    def get_input_alias(
        self,
        provider: str,
        input_name: str,
        input_type: str,
        is_array: bool = False,
        array_index: int = 1
    ) -> Optional[str]:
        """
        Get the alias name for an input field.
        
        Args:
            provider: Provider name (replicate, falai, huggingface)
            input_name: The input field name from schema
            input_type: ComfyUI type (IMAGE, AUDIO, VIDEO)
            is_array: Whether this is an array input
            array_index: Index for array inputs (1-based)
            
        Returns:
            Alias name or None if not found
        """
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_inputs = self.global_inputs.get(provider_key, {})
        inputs_config = provider_inputs.get('inputs', {})
        
        # Check for matching input pattern
        for pattern_name, input_config in inputs_config.items():
            if not isinstance(input_config, dict):
                continue
            
            # Get field match patterns
            field_match = input_config.get('field_match', {})
            if isinstance(field_match, dict):
                name_patterns = field_match.get('name_patterns', [])
                
                # Check if input name matches any pattern
                input_lower = input_name.lower()
                for pattern in name_patterns:
                    if pattern.lower() in input_lower or input_lower in pattern.lower():
                        # Found matching pattern, return alias
                        alias = input_config.get('alias')
                        if alias:
                            # For arrays, add suffix with index
                            if is_array:
                                suffix = input_config.get('alias_array_suffix', '_1')
                                # Replace _1 with actual index
                                alias = alias + suffix.replace('_1', f'_{array_index}')
                            return alias
        
        # Default aliases based on input type
        default_aliases = {
            'IMAGE': 'IMAGE',
            'AUDIO': 'AUDIO',
            'VIDEO': 'VIDEO',
        }
        
        if input_type:
            base_alias = default_aliases.get(input_type.upper(), input_type)
            # For array inputs, always add numbered suffix (IMAGE_1, IMAGE_2, etc.)
            if is_array and array_index >= 1:
                return f"{base_alias}_{array_index}"
            return base_alias
        
        return None
    
    def get_max_images(self, provider: str, model_id: str) -> int:
        """Get max_images setting for a model."""
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            return model_config.get('max_images', 0)
        
        provider_config = self.config.get(provider.lower(), {})
        global_max = provider_config.get('global', {}).get('max_images', 0)
        
        # Legacy JSON format support
        if 'max_images' in provider_config:
            return provider_config['max_images'].get(model_id, 0)
        
        return global_max
    
    def get_array_input_field(self, provider: str, model_id: str) -> Optional[str]:
        """Get the array input field name for a model."""
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            return model_config.get('array_input_field')
        
        # Legacy JSON format support
        provider_config = self.config.get(provider.lower(), {})
        if 'array_input_fields' in provider_config:
            return provider_config['array_input_fields'].get(model_id)
        
        return None
    
    def get_model_inputs(
        self, 
        provider: str, 
        model_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get input field definitions for a model.
        
        Returns a dict mapping field names to their configuration:
        - type: ComfyUI input type (IMAGE, AUDIO, VIDEO, STRING)
        - is_array: Whether the field accepts multiple items
        - max_items: Maximum number of items (if array)
        - group: Parameter group (basic, advanced, etc.)
        - order: Sort order within group
        """
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            return model_config.get('inputs', {})
        
        return {}
    
    def get_model_parameters(
        self, 
        provider: str, 
        model_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get parameter definitions for a model.
        
        Returns a dict mapping parameter names to their configuration:
        - group: Parameter group (system, basic, advanced)
        - order: Sort order within group
        - widget: ComfyUI widget type override (e.g., "seed")
        """
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            return model_config.get('parameters', {})
        
        return {}
    
    def get_model_outputs(
        self, 
        provider: str, 
        model_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get output definitions for a model.
        
        Returns a dict mapping output names to their configuration:
        - type: ComfyUI output type (IMAGE, AUDIO, VIDEO, STRING)
        - is_array: Whether output is an array
        - source: Source path for complex outputs (e.g., "images[].url")
        """
        model_config = self.get_model_config(provider, model_id)
        if model_config:
            return model_config.get('outputs', {})
        
        return {}
    
    def get_parameter_groups(
        self, 
        provider: str
    ) -> Dict[str, List[str]]:
        """Get parameter group ordering and membership from global_parameters.yaml."""
        # Map provider name to config key
        provider_key_map = {
            'replicate': 'replicate_api',
            'falai': 'fal_ai_api',
            'huggingface': 'huggingface_api',
        }
        provider_key = provider_key_map.get(provider.lower(), provider.lower())
        provider_params = self.global_parameters.get(provider_key, {})
        return provider_params.get('parameter_groups', {})


# Singleton instance
_config_loader = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Get the configuration loader singleton.
    
    Args:
        config_path: Optional path to config file (only used on first call)
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
        if config_path:
            _config_loader.reload(config_path)
    return _config_loader


def reload_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    Reload configuration from file.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Reloaded ConfigLoader instance
    """
    global _config_loader
    _config_loader = ConfigLoader()
    if config_path:
        _config_loader.reload(config_path)
    return _config_loader


# Convenience functions that mirror the old JSON-based API
def load_model_config(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Load model configuration (legacy function for compatibility).
    
    Args:
        model_name: Full model name (e.g., "replicate/model:version")
        
    Returns:
        Model configuration dictionary
    """
    # Parse provider from model name format
    if '/' in model_name:
        parts = model_name.split('/')
        provider = parts[0].lower()
        model_id = '/'.join(parts[1:]).split(':')[0]
    else:
        return None
    
    config = get_config()
    return config.get_model_config(provider, model_id)


def get_configured_max_images(model_name: str) -> int:
    """
    Get max_images for a model.
    
    Args:
        model_name: Full model name
        
    Returns:
        Maximum number of images (0 = not set)
    """
    parts = model_name.replace(':', '/').split('/')
    provider = parts[0].lower()
    model_id = '/'.join(parts[1:])
    
    config = get_config()
    return config.get_max_images(provider, model_id)


def get_configured_array_input(model_name: str) -> Optional[str]:
    """
    Get array input field for a model.
    
    Args:
        model_name: Full model name
        
    Returns:
        Array input field name or None
    """
    parts = model_name.replace(':', '/').split('/')
    provider = parts[0].lower()
    model_id = '/'.join(parts[1:])
    
    config = get_config()
    return config.get_array_input_field(provider, model_id)
