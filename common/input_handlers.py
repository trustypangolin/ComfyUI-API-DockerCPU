"""
Input processing utilities for ComfyUI-API-DockerCPU

Provides common utilities for:
- Processing array inputs from ComfyUI
- Removing falsey optional inputs
- Converting input images to base64
"""

from typing import Dict, Any, List, Optional

import torch


def handle_array_inputs(
    kwargs: Dict[str, Any],
    array_inputs: List[str]
) -> None:
    """
    Convert string array inputs to proper arrays.
    
    Modifies kwargs in-place.
    
    Args:
        kwargs: Dictionary of input parameters
        array_inputs: List of input names that should be arrays
        
    Examples:
        >>> kwargs = {"images": "url1\nurl2\nurl3"}
        >>> handle_array_inputs(kwargs, ["images"])
        >>> kwargs["images"]
        ['url1', 'url2', 'url3']
        
        >>> kwargs = {"images": "single_url"}
        >>> handle_array_inputs(kwargs, ["images"])
        >>> kwargs["images"]
        ['single_url']
    """
    for input_name in array_inputs:
        if input_name in kwargs:
            if isinstance(kwargs[input_name], str):
                kwargs[input_name] = (
                    kwargs[input_name].split("\n") if kwargs[input_name] else []
                )
            elif not isinstance(kwargs[input_name], list):
                kwargs[input_name] = [kwargs[input_name]]
