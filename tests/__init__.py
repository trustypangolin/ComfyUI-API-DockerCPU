"""
Tests for ComfyUI-API-DockerCPU

This module provides tests that can be run outside of ComfyUI
to validate schemas, inputs, outputs, and utility functions.

Run with: python -m pytest tests/
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
