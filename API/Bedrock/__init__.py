"""
Amazon Bedrock integration for ComfyUI-API-DockerCPU.

Auth is a named AWS profile (normally IAM Roles Anywhere via aws/rolesanywhere.sh);
AWS_BEDROCK_PROFILE in .env picks the default.
"""

from .node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
