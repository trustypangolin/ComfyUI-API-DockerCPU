"""
Logging utilities for ComfyUI-API-DockerCPU

Provides structured logging capabilities for debugging and monitoring.
"""

import os
import json
from typing import Any, Dict, Optional

from .utils import format_value_for_log, convert_to_json_serializable


# Global logger configuration
_LOG_PREFIX = "[ComfyUI-API-DockerCPU]"
_DEBUG_MODE = os.environ.get("DEBUG_API_TRUSTYPANGOLIN", "false").lower() == "true"


def setup_logger(prefix: str = None, debug: bool = None) -> None:
    """
    Configure the global logger settings.
    
    Args:
        prefix: Custom prefix for log messages
        debug: Enable debug mode globally
    """
    global _LOG_PREFIX, _DEBUG_MODE
    
    if prefix is not None:
        _LOG_PREFIX = prefix
    if debug is not None:
        _DEBUG_MODE = debug


def get_logger(name: str) -> 'NodeLogger':
    """
    Get a logger instance for a specific component.
    
    Args:
        name: Name of the component (e.g., "Replicate", "FalAi")
        
    Returns:
        NodeLogger instance
    """
    return NodeLogger(name)


class NodeLogger:
    """
    Structured logger for API nodes.
    
    Provides methods for logging inputs, outputs, and errors
    in a consistent format across all API integrations.
    """
    
    def __init__(self, name: str, category: str = "API"):
        """
        Initialize the logger.
        
        Args:
            name: Name of the node/API (e.g., "Replicate", "FalAi")
            category: Category prefix for the log messages
        """
        self.name = name
        self.category = category
        self.prefix = f"[{self.category} {self.name}]"
    
    def info(self, message: str) -> None:
        """Log an info message."""
        print(f"\033[94m{_LOG_PREFIX} {self.prefix} {message}\033[0m")
    
    def success(self, message: str) -> None:
        """Log a success message."""
        print(f"\033[92m{_LOG_PREFIX} {self.prefix} {message}\033[0m")
    
    def warning(self, message: str) -> None:
        """Log a warning message."""
        print(f"\033[93m{_LOG_PREFIX} {self.prefix} {message}\033[0m")
    
    def error(self, message: str) -> None:
        """Log an error message."""
        print(f"\033[91m{_LOG_PREFIX} {self.prefix} {message}\033[0m")
    
    def debug(self, message: str) -> None:
        """Log a debug message (only if debug mode is enabled)."""
        if _DEBUG_MODE:
            print(f"\033[96m{_LOG_PREFIX} {self.prefix} [DEBUG] {message}\033[0m")
    
    def log_input(self, kwargs: Dict[str, Any]) -> None:
        """
        Log input parameters with formatting for large data.
        
        Args:
            kwargs: Dictionary of input parameters
        """
        formatted_kwargs = {k: format_value_for_log(v) for k, v in kwargs.items()}
        self.debug(f"Input parameters: {json.dumps(formatted_kwargs, indent=2)}")
    
    def log_output(self, output: Any) -> None:
        """
        Log output with formatting for large data.
        
        Args:
            output: Output data
        """
        formatted_output = convert_to_json_serializable(output)
        self.debug(f"Output: {json.dumps(formatted_output, indent=2)[:500]}...")
    
    def log_api_call(self, model_name: str, params: Dict[str, Any]) -> None:
        """
        Log an API call with parameters.
        
        Args:
            model_name: Name of the model being called
            params: API call parameters
        """
        self.info(f"Calling {model_name}")
        formatted_params = {k: format_value_for_log(v) for k, v in params.items()}
        self.debug(f"Parameters: {json.dumps(formatted_params, indent=2)}")
    
    def log_api_response(self, response: Any) -> None:
        """
        Log an API response.
        
        Args:
            response: API response data
        """
        self.debug(f"Response received")
        formatted_response = convert_to_json_serializable(response)
        self.debug(f"Response: {str(formatted_response)[:500]}")
    
    def log_token_status(self, token_name: str, present: bool) -> None:
        """
        Log the status of an API token.
        
        Args:
            token_name: Name of the token (e.g., "REPLICATE_API_TOKEN")
            present: Whether the token is present
        """
        status = "\033[93mfound\033[0m" if present else "\033[91mmissing\033[0m"
        message = f"Loaded API, {token_name} Environment variable {status}"
        if not present:
            message += " (did you export/set the variable?)"
        print(f"\033[94m{_LOG_PREFIX} {self.prefix} {message}\033[0m")


def log_node_input(
    node_name: str,
    kwargs: Dict[str, Any],
    include_json: bool = True
) -> Optional[str]:
    """
    Log node inputs and optionally return formatted JSON.
    
    Args:
        node_name: Name of the node
        kwargs: Input parameters
        include_json: Whether to return formatted JSON string
        
    Returns:
        Formatted JSON string if include_json is True, None otherwise
    """
    logger = get_logger(node_name)
    logger.log_input(kwargs)
    
    if include_json:
        serializable_kwargs = convert_to_json_serializable(kwargs)
        return json.dumps(serializable_kwargs, indent=2)
    
    return None


def log_debug_mode_info(node_name: str, input_json: str) -> None:
    """
    Log information when running in debug/dry-run mode.
    
    Args:
        node_name: Name of the node
        input_json: JSON string of input parameters
    """
    logger = get_logger(node_name)
    logger.debug("DEBUG MODE: Skipping API call, returning input data")
    logger.debug(f"Input JSON: {input_json}")
