"""
HuggingFace API Nodes for ComfyUI-API-DockerCPU

Provides:
- Model selector node for browsing HF repos
- Lora URL builder and combiner nodes
- Schema-based inference nodes
- Debug/dry-run mode for all nodes
"""

import os
import json
import time
from typing import Dict, Any, Tuple, List, Optional

try:
    from huggingface_hub import HfApi, login
    from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    HfApi = None
    login = None
    GatedRepoError = None
    RepositoryNotFoundError = None

from .schema_to_node import (
    schema_to_comfyui_input_types,
    get_return_type,
    name_and_version,
)


# ============================================================================
# Configuration
# ============================================================================

def get_supported_repos() -> List[str]:
    """Load supported repositories from supported_models.json (huggingface.repos section)."""
    package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config_path = os.path.join(package_dir, "supported_models.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            hf_config = config.get("huggingface", {})
            return hf_config.get("repos", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_hf_api() -> Optional["HfApi"]:
    """Initialize and return the HuggingFace API client."""
    if not HF_AVAILABLE:
        return None
    
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("[ComfyUI-API-HuggingFace] Warning: HF_TOKEN environment variable not set")
        return None
    
    try:
        login(token=token)
        return HfApi()
    except Exception as e:
        print(f"[ComfyUI-API-HuggingFace] Warning: Failed to authenticate with HuggingFace: {e}")
        return None


def build_safetensor_url(repo_id: str, filename: str) -> str:
    """Build the HuggingFace direct download URL for a safetensor file."""
    return f"https://huggingface.co/{repo_id}/resolve/main/{filename}"


# ============================================================================
# Model Cache
# ============================================================================

class ModelCache:
    """Simple in-memory cache for model listings."""
    
    def __init__(self):
        self._cache: Dict[str, List[str]] = {}
    
    def get(self, key: str) -> Optional[List[str]]:
        return self._cache.get(key)
    
    def set(self, key: str, value: List[str]) -> None:
        self._cache[key] = value
    
    def clear(self) -> None:
        self._cache.clear()


_file_cache = ModelCache()


# ============================================================================
# Schema-based Models (from import_schemas.py)
# ============================================================================

SCHEMAS_DIR = None  # Will be lazily initialized


def get_schemas_dir() -> str:
    """Get the schemas directory for HuggingFace."""
    global SCHEMAS_DIR
    if SCHEMAS_DIR is None:
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        SCHEMAS_DIR = os.path.join(package_dir, "schemas", "HuggingFace")
    return SCHEMAS_DIR


def load_schema_for_repo(repo_id: str) -> Optional[Dict]:
    """
    Load schema JSON for a specific repository from schemas/HuggingFace/.
    
    Args:
        repo_id: HuggingFace repository ID (e.g., "renderartist/Model")
        
    Returns:
        Schema dictionary or None if not found
    """
    schema_filename = f"{repo_id.replace('/', '_')}.json"
    schema_path = os.path.join(get_schemas_dir(), schema_filename)
    
    try:
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def load_all_schemas() -> List[Dict]:
    """
    Load all schema JSON files from schemas/HuggingFace/.
    
    Returns:
        List of schema dictionaries
    """
    schemas_dir = get_schemas_dir()
    schemas = []
    
    if not os.path.exists(schemas_dir):
        return schemas
    
    for filename in os.listdir(schemas_dir):
        if filename.endswith(".json"):
            schema_path = os.path.join(schemas_dir, filename)
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                    schemas.append(schema)
            except (json.JSONDecodeError, IOError):
                continue
    
    return schemas


def get_safetensors_for_repo(repo_id: str) -> List[str]:
    """
    Get the list of safetensors for a specific repository from schema.
    
    Args:
        repo_id: HuggingFace repository ID
        
    Returns:
        List of safetensor filenames
    """
    schema = load_schema_for_repo(repo_id)
    if schema:
        models = schema.get("models", [])
        return [m.get("filename", m.get("path", "")) for m in models if m]
    return []


def load_extracted_models() -> Dict[str, List[str]]:
    """
    Load all repos and their models from schema files.
    
    Returns:
        Dictionary mapping repo_id to list of safetensor filenames
    """
    repos = {}
    schemas = load_all_schemas()
    
    for schema in schemas:
        repo_id = schema.get("repo_id")
        if repo_id:
            models = schema.get("models", [])
            repos[repo_id] = [m.get("filename", m.get("path", "")) for m in models if m]
    
    return repos


def list_safetensors(repo_id: str, force_refresh: bool = False) -> List[str]:
    """
    List all .safetensors files in a repository.
    
    First checks local schema cache, then falls back to API if needed.
    
    Args:
        repo_id: The HuggingFace repository ID
        force_refresh: Force refresh from API (if schema not found locally)
        
    Returns:
        List of safetensor filenames
    """
    # First check local schema cache
    if not force_refresh:
        cached = _file_cache.get(repo_id)
        if cached is not None:
            return cached
        
        # Try to load from schema file
        schema = load_schema_for_repo(repo_id)
        if schema and schema.get("models"):
            models = schema.get("models", [])
            safetensors = [m.get("filename", m.get("path", "")) for m in models if m]
            _file_cache.set(repo_id, safetensors)
            return safetensors
    
    # Fallback to API call
    api = get_hf_api()
    if api is None:
        # Return cached or empty
        return _file_cache.get(repo_id) or []
    
    try:
        files_info = api.list_repo_files(repo_id=repo_id, revision="main")
        safetensors = [f for f in files_info if f.endswith(".safetensors")]
        safetensors.sort()
        _file_cache.set(repo_id, safetensors)
        return safetensors
    except (RepositoryNotFoundError, GatedRepoError, Exception):
        return []


def refresh_safetensor_options() -> Dict[str, List[str]]:
    """
    Refresh safetensor options from both extracted models and API.
    
    Returns:
        Dictionary mapping repo_id to list of safetensor filenames
    """
    repos = get_supported_repos()
    all_options = {}
    
    # First try extracted models (pre-fetched)
    extracted = load_extracted_models()
    for repo_id in repos:
        files = extracted.get(repo_id, [])
        if files:
            all_options[repo_id] = files
        else:
            # Fallback to API
            files = list_safetensors(repo_id, force_refresh=True)
            if files:
                all_options[repo_id] = files
    
    return all_options


# ============================================================================
# Node 1: HuggingFace Model Selector
# ============================================================================

class HuggingFaceModelSelector:
    """
    ComfyUI node for selecting safetensor models from HuggingFace repositories.
    """
    
    @classmethod
    def IS_CHANGED(cls, **kwargs) -> str:
        """Force re-evaluation."""
        return str(time.time())
    
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define node inputs with all safetensors listed."""
        all_options = refresh_safetensor_options()
        
        all_safetensors = []
        for repo_id, files in all_options.items():
            for f in files:
                labeled = f"[{repo_id}] {f}"
                all_safetensors.append(labeled)
        
        default_safetensor = all_safetensors[0] if all_safetensors else "-- No safetensors available --"
        
        return {
            "required": {
                "safetensor_file": (
                    all_safetensors if all_safetensors else ["-- No safetensors available --"],
                    {"default": default_safetensor}
                ),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_url",)
    FUNCTION = "select_model"
    CATEGORY = "🎨 DockerCPU API/🤗 HuggingFace"
    OUTPUT_NODE = False
    
    def select_model(self, safetensor_file: str, **kwargs) -> Tuple[str]:
        """Select a safetensor and return its URL."""
        if not safetensor_file or safetensor_file.startswith("--"):
            return ("",)
        
        # Extract repo_id and filename from prefixed format: "[repo_id] filename"
        if safetensor_file.startswith("[") and "] " in safetensor_file:
            parts = safetensor_file.split("] ", 1)
            if len(parts) == 2:
                repo_id = parts[0][1:]
                filename = parts[1]
                return (build_safetensor_url(repo_id, filename),)
        
        return ("",)


# ============================================================================
# Node 2: Lora Weights Combiner
# ============================================================================

class LoraWeightsCombiner:
    """
    ComfyUI node for combining multiple Lora weight URLs into an array.
    """
    
    NUM_LORA_SLOTS = 5
    
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define node inputs."""
        lora_inputs = {}
        
        for i in range(1, cls.NUM_LORA_SLOTS + 1):
            lora_inputs[f"lora_{i}"] = (
                "STRING",
                {
                    "default": "",
                    "tooltip": f"Lora {i} URL (optional, leave empty to skip)",
                }
            )
        
        return {
            "required": {
                "output_format": (
                    ["python_list", "json_string"],
                    {
                        "default": "python_list",
                        "tooltip": "Output format:\n• python_list: ['url1', 'url2']\n• json_string: '[\"url1\", \"url2\"]'",
                    }
                ),
            },
            "optional": lora_inputs,
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lora_weights",)
    FUNCTION = "combine_loras"
    CATEGORY = "🎨 DockerCPU API/🤗 HuggingFace"
    OUTPUT_NODE = True
    
    def combine_loras(
        self,
        output_format: str,
        lora_1: str = "",
        lora_2: str = "",
        lora_3: str = "",
        lora_4: str = "",
        lora_5: str = "",
        **kwargs
    ) -> Tuple[str]:
        """Combine multiple Lora URLs into a single output."""
        lora_urls = []
        for i in range(1, self.NUM_LORA_SLOTS + 1):
            url = locals()[f"lora_{i}"]
            if url and url.strip():
                lora_urls.append(url.strip())
        
        if not lora_urls:
            return ('[]',) if output_format == "json_string" else ('[]',)
        
        if output_format == "json_string":
            return (json.dumps(lora_urls),)
        else:
            return (str(lora_urls),)


# ============================================================================
# Node 3: Lora URL Builder
# ============================================================================

class LoraUrlBuilder:
    """
    Utility node for building HuggingFace Lora URLs from components.
    """
    
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define node inputs."""
        return {
            "required": {
                "repo_id": (
                    "STRING",
                    {
                        "default": "",
                        "placeholder": "e.g., renderartist/Technically-Color-Z-Image-Turbo",
                    }
                ),
                "filename": (
                    "STRING",
                    {
                        "default": "",
                        "placeholder": "e.g., model.safetensors",
                    }
                ),
            },
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lora_url",)
    FUNCTION = "build_url"
    CATEGORY = "🎨 DockerCPU API/🤗 HuggingFace"
    OUTPUT_NODE = False
    
    def build_url(self, repo_id: str, filename: str) -> Tuple[str]:
        """Build the full HuggingFace URL."""
        if not repo_id or not filename:
            return ("",)
        
        repo_id = repo_id.strip()
        filename = filename.strip()
        
        if not filename.endswith(".safetensors"):
            filename = f"{filename}.safetensors"
        
        return (build_safetensor_url(repo_id, filename),)


# ============================================================================
# Node Export
# ============================================================================

NODE_CLASS_MAPPINGS = {
    "HFModelSelector": HuggingFaceModelSelector,
    "HFLoraCombiner": LoraWeightsCombiner,
    "HFLoraUrlBuilder": LoraUrlBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HFModelSelector": "HF Model Selector",
    "HFLoraCombiner": "HF Lora Combiner",
    "HFLoraUrlBuilder": "HF Lora URL Builder",
}


def create_nodes(schemas_dir: str = None) -> Dict[str, type]:
    """
    Create all ComfyUI nodes from schema files.
    
    For HuggingFace, schemas are optional as most HF models
    don't have standard schema formats. This returns the utility nodes.
    
    Args:
        schemas_dir: Directory containing JSON schema files (optional)
        
    Returns:
        Dictionary mapping node names to node classes
    """
    return NODE_CLASS_MAPPINGS.copy()
