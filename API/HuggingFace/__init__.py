"""
HuggingFace API integration for ComfyUI-API-DockerCPU

This module provides:
- Schema-to-node conversion for HuggingFace models
- Utility nodes for model selection and URL building
- API client initialization
"""

from .node import create_nodes, NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
from .schema_to_node import (
    schema_to_comfyui_input_types,
    get_return_type,
    name_and_version,
)

__all__ = [
    "create_nodes",
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "schema_to_comfyui_input_types",
    "get_return_type",
    "name_and_version",
]
