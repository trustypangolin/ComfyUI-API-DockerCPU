"""
ComfyUI API Integration Tests

Tests the ComfyUI API endpoints to ensure nodes work correctly.
Requires ComfyUI to be running on localhost:8188 (or configured URL).

Run with:
    . venv/bin/activate && python -m pytest tests/test_api.py -v -s
"""

import json
import os
import sys
from typing import Dict, Any, Optional

import pytest

# Add project root to path
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# ComfyUI API configuration
COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "http://comfy.localhost")
PROMPT_URL = f"{COMFYUI_HOST}/prompt"
HISTORY_URL = f"{COMFYUI_HOST}/history"
SYSTEM_STATS_URL = f"{COMFYUI_HOST}/system_stats"


def is_comfyui_running() -> bool:
    """Check if ComfyUI is running."""
    try:
        import urllib.request
        from urllib.parse import urlparse
        
        parsed = urlparse(COMFYUI_HOST)
        req = urllib.request.Request(f"{COMFYUI_HOST}/system_stats")
        req.add_header('Host', parsed.hostname)
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception:
        return False


def queue_prompt(prompt: Dict[str, Any]) -> Optional[str]:
    """
    Queue a prompt to ComfyUI API.
    
    Args:
        prompt: The prompt dictionary to queue
        
    Returns:
        The prompt ID if successful, None otherwise
    """
    try:
        import urllib.request
        from urllib.parse import urlparse
        
        parsed = urlparse(COMFYUI_HOST)
        data = json.dumps({"prompt": prompt}).encode("utf-8")
        req = urllib.request.Request(
            PROMPT_URL,
            data=data,
            headers={"Content-Type": "application/json", "Host": parsed.hostname}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("prompt_id")
            
    except Exception as e:
        print(f"Failed to queue prompt: {e}")
        return None


def get_history(prompt_id: str) -> Optional[Dict[str, Any]]:
    """Get the history for a prompt."""
    try:
        import urllib.request
        from urllib.parse import urlparse
        
        parsed = urlparse(COMFYUI_HOST)
        url = f"{HISTORY_URL}/{prompt_id}"
        req = urllib.request.Request(url)
        req.add_header('Host', parsed.hostname)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get(prompt_id)
            
    except Exception as e:
        print(f"Failed to get history: {e}")
        return None


class TestComfyUIAPI:
    """Test suite for ComfyUI API integration."""
    
    @pytest.fixture(autouse=True)
    def check_comfyui(self):
        """Ensure ComfyUI is running before tests."""
        if not is_comfyui_running():
            pytest.skip("ComfyUI is not running. Start it with: docker-compose up -d")
    
    def test_comfyui_api_reachable(self):
        """Test that ComfyUI API is reachable."""
        import urllib.request
        from urllib.parse import urlparse
        
        parsed = urlparse(COMFYUI_HOST)
        req = urllib.request.Request(SYSTEM_STATS_URL)
        req.add_header('Host', parsed.hostname)
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))
            assert "system" in data
    
    def test_load_replicate_workflow(self):
        """Test loading a Replicate workflow via API."""
        # Create a simple text-to-image workflow (no image input required)
        workflow = {
            "1": {
                "inputs": {
                    "dry_run": True,
                    "force_rerun": False,
                    "prompt": "A beautiful sunset over the ocean",
                    "seed": 0,
                    "lora_scales": "",
                    "aspect_ratio": "1:1",
                    "output_megapixels": "1",
                    "output_format": "jpg",
                    "output_quality": 95,
                    "disable_safety_checker": False,
                },
                "class_type": "Replicate black-forest-labs/flux-2-klein-9b-base-lora",
            },
            "2": {
                "inputs": {
                    "images": ["1", 0]
                },
                "class_type": "PreviewImage",
            }
        }
        
        # Queue the prompt
        prompt_id = queue_prompt(workflow)
        assert prompt_id is not None, "Failed to queue prompt"
        
        print(f"Queued prompt: {prompt_id}")
        
        # Get the history (in dry_run mode, this should be fast)
        import time
        time.sleep(2)  # Wait for processing
        
        history = get_history(prompt_id)
        assert history is not None, "Failed to get history"
        
        # Check status
        status = history.get("status", {})
        assert "state" in status
        
        print(f"Workflow status: {status}")
        
        # In dry_run mode, expect succeeded status
        assert status.get("state") in ["succeeded", "completed"], f"Unexpected state: {status.get('state')}"
    
    def test_load_flux_workflow(self):
        """Test loading a FLUX generation workflow via API."""
        # Create a simple FLUX text-to-image workflow
        workflow = {
            "1": {
                "inputs": {
                    "dry_run": True,
                    "force_rerun": False,
                    "prompt": "A futuristic city at sunset, digital art",
                    "seed": 42,
                    "aspect_ratio": "16:9",
                    "output_format": "png",
                },
                "class_type": "Replicate black-forest-labs/flux-2-klein-9b",
            },
            "2": {
                "inputs": {
                    "images": ["1", 0]  # From node 1 output 0
                },
                "class_type": "PreviewImage",
            }
        }
        
        # Queue the prompt
        prompt_id = queue_prompt(workflow)
        assert prompt_id is not None, "Failed to queue prompt"
        
        print(f"Queued FLUX prompt: {prompt_id}")
        
        # Get the history
        import time
        time.sleep(2)
        
        history = get_history(prompt_id)
        assert history is not None, "Failed to get history"
        
        status = history.get("status", {})
        assert status.get("state") in ["succeeded", "completed"]
        
        print(f"FLUX workflow status: {status}")


def run_api_tests():
    """Run API tests manually without pytest."""
    print("=" * 60)
    print("ComfyUI API Tests")
    print("=" * 60)
    
    if not is_comfyui_running():
        print("⚠️  ComfyUI is not running.")
        print("   Start it with: docker-compose up -d")
        print("   Or set COMFYUI_HOST environment variable if running elsewhere.")
        return
    
    print("✓ ComfyUI is reachable")
    
    # Run a simple workflow test
    workflow = {
        "1": {
            "inputs": {
                "dry_run": True,
                "force_rerun": False,
                "prompt": "Test prompt",
                "seed": 123,
                "aspect_ratio": "1:1",
            },
            "class_type": "Replicate black-forest-labs/flux-2-klein-9b",
        }
    }
    
    print("\nTesting Replicate workflow...")
    prompt_id = queue_prompt(workflow)
    
    if prompt_id:
        print(f"✓ Prompt queued: {prompt_id}")
        
        import time
        time.sleep(2)
        
        history = get_history(prompt_id)
        if history:
            print(f"✓ History retrieved: {history.get('status', {})}")
        else:
            print("✗ Failed to get history")
    else:
        print("✗ Failed to queue prompt")
    
    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    run_api_tests()
