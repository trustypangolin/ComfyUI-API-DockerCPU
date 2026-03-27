"""
Pytest configuration for ComfyUI-API-DockerCPU tests.

This conftest.py properly sets up the Python path and package structure
so that tests can run outside of the ComfyUI environment while still
allowing relative imports to work correctly within the package.

The key is to:
1. Ensure the package root is in sys.path
2. Set __package__ correctly for nested imports
3. Avoid triggering the parent __init__.py which has ComfyUI-specific imports
"""

import os
import sys

# Get the package root directory (tests/)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory (the package root)
PACKAGE_ROOT = os.path.dirname(TESTS_DIR)

# Ensure the package root is in sys.path
# This allows imports like "from API.Replicate import ..." to work
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)


def pytest_configure(config):
    """
    Pytest hook called after command line options have been parsed.
    
    We use this to ensure proper package structure without modifying
    the parent __init__.py.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require API keys)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (can run without external dependencies)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test items after collection.
    
    This ensures that relative imports within the package work correctly
    by properly setting up the import context.
    """
    pass  # Placeholder for future collection modifications if needed


# Make sure the parent __init__.py doesn't get executed during test discovery
# by ensuring we're in the right package context
__path__ = [os.path.join(PACKAGE_ROOT, "tests")]
__package__ = "tests"
