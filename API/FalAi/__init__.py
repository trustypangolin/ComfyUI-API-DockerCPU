"""
FalAi API integration for ComfyUI-API-DockerCPU

This module provides:
- Schema-to-node conversion for Fal.ai models
- Node creation from OpenAPI schemas
- API client initialization
"""

from .node import create_nodes
from .schema_to_node import (
    schema_to_comfyui_input_types,
    get_return_type,
    name_and_version,
    inputs_that_need_arrays,
)

__all__ = [
    "create_nodes",
    "schema_to_comfyui_input_types",
    "get_return_type",
    "name_and_version",
    "inputs_that_need_arrays",
]
