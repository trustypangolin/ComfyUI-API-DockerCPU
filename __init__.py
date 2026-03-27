"""
ComfyUI-API-DockerCPU - Unified API Integration for ComfyUI

This package combines multiple external API integrations into a single
ComfyUI custom node extension:

- Replicate API (🎨 DockerCPU API/Replicate)
- Fal.ai API (🎨 DockerCPU API/FalAi)
- HuggingFace Hub (🎨 DockerCPU API/🤗 HuggingFace)

All nodes support debug/dry-run mode for testing workflows without API costs.

Environment Variables:
- REPLICATE_API_TOKEN: Required for Replicate API
- FAL_KEY: Required for Fal.ai API
- HF_TOKEN: Optional for HuggingFace (required for private repos)
- DEBUG_API_TRUSTYPANGOLIN: Set to "true" to enable debug output

Usage:
1. Install dependencies: pip install -r requirements.txt
2. Set required environment variables
3. Run 'python refresh_models.py' for HuggingFace
4. Import schemas: python import_schemas.py (for Replicate/FalAi)
5. Install in ComfyUI as a custom node extension
"""

import os
import sys

# Detect if we're in a test context (pytest is running tests)
# This allows the package to be imported without triggering ComfyUI-specific
# relative imports that would fail outside the ComfyUI environment
def _is_test_context() -> bool:
    """Check if we're running in a test context."""
    # Check if pytest is running
    if "pytest" in sys.modules:
        return True
    
    # Check if we're being imported from the tests directory
    frame = sys._getframe()
    while frame:
        if frame.f_code.co_filename.endswith("tests"):
            return True
        frame = frame.f_back
    
    return False

# Check for API tokens and display status
def _check_api_tokens():
    """Check and display API token status on load."""
    tokens = {
        "REPLICATE_API_TOKEN": "Replicate",
        "FAL_KEY": "Fal.ai",
        "HF_TOKEN": "HuggingFace",
    }
    
    for env_var, api_name in tokens.items():
        if os.environ.get(env_var):
            print(f"\033[94m[ComfyUI-API-DockerCPU] Loaded API, {api_name} token \033[92mfound\033[0m\033[94m\033[0m")
        else:
            # Check if token is required
            required = env_var != "HF_TOKEN"
            status = "\033[91mmissing\033[0m\033[94m" if required else "\033[93moptional\033[0m\033[94m"
            hint = " (did you export/set the variable?)" if required else " (optional)"
            print(f"\033[94m[ComfyUI-API-DockerCPU] Loaded API, {api_name} token {status}{hint}\033[0m")

_check_api_tokens()

# Import all node classes from API modules
# In test context, we skip these imports to avoid relative import errors
# Tests will manually import what they need from the API modules directly
if not _is_test_context():
    from .API.Replicate import create_nodes as create_replicate_nodes
    from .API.FalAi import create_nodes as create_falai_nodes
    from .API.HuggingFace import (
        create_nodes as create_huggingface_nodes,
        NODE_CLASS_MAPPINGS as HF_NODE_CLASS_MAPPINGS,
        NODE_DISPLAY_NAME_MAPPINGS as HF_NODE_DISPLAY_NAME_MAPPINGS,
    )

    # Create node mappings from each API
    _replicate_nodes = {}
    _falai_nodes = {}
    _huggingface_nodes = {}

    # Try to load nodes (may fail if schemas not present)
    try:
        _replicate_nodes = create_replicate_nodes()
    except Exception as e:
        print(f"[ComfyUI-API-DockerCPU] Warning: Could not load Replicate nodes: {e}")

    try:
        _falai_nodes = create_falai_nodes()
    except Exception as e:
        print(f"[ComfyUI-API-DockerCPU] Warning: Could not load Fal.ai nodes: {e}")

    try:
        _huggingface_nodes = create_huggingface_nodes()
    except Exception as e:
        print(f"[ComfyUI-API-DockerCPU] Warning: Could not load HuggingFace nodes: {e}")

    # Combine all node mappings
    NODE_CLASS_MAPPINGS = {}
    NODE_CLASS_MAPPINGS.update(_replicate_nodes)
    NODE_CLASS_MAPPINGS.update(_falai_nodes)
    NODE_CLASS_MAPPINGS.update(_huggingface_nodes)

    # Display loaded nodes
    if NODE_CLASS_MAPPINGS:
        print(f"[ComfyUI-API-DockerCPU] Loaded {len(NODE_CLASS_MAPPINGS)} nodes:")
        print(f"  - Replicate: {len(_replicate_nodes)} nodes")
        print(f"  - Fal.ai: {len(_falai_nodes)} nodes")
        print(f"  - HuggingFace: {len(_huggingface_nodes)} nodes")
    else:
        print("[ComfyUI-API-DockerCPU] Warning: No nodes loaded. Check schema files.")

    # Display name mappings
    NODE_DISPLAY_NAME_MAPPINGS = {}
    if _huggingface_nodes:
        from .API.HuggingFace import NODE_DISPLAY_NAME_MAPPINGS as HF_DISPLAY
        NODE_DISPLAY_NAME_MAPPINGS.update(HF_DISPLAY)
else:
    # Test context: provide empty placeholders
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    _replicate_nodes = {}
    _falai_nodes = {}
    _huggingface_nodes = {}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
]

# Run tests if DEBUG_API_TRUSTYPANGOLIN is set
if os.environ.get("DEBUG_API_TRUSTYPANGOLIN", "false").lower() == "true":
    print("[ComfyUI-API-DockerCPU] DEBUG mode enabled, checking for tests...")
    import importlib.util
    import sys
    
    # Get the tests directory path
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')
    
    if os.path.exists(tests_dir):
        # Try to import and run tests
        test_schema_path = os.path.join(tests_dir, "test_schemas.py")
        if os.path.exists(test_schema_path):
            try:
                spec = importlib.util.spec_from_file_location("test_schemas", test_schema_path)
                test_module = importlib.util.module_from_spec(spec)
                sys.modules["test_schemas"] = test_module
                spec.loader.exec_module(test_module)
                print("[ComfyUI-API-DockerCPU] Tests completed successfully")
            except Exception as e:
                print(f"[ComfyUI-API-DockerCPU] Test error: {e}")
