#!/usr/bin/env python3
"""
Import Schemas Script for ComfyUI-API-DockerCPU

This script fetches and updates model schemas from external APIs:
- Replicate API schemas
- Fal.ai API schemas
- HuggingFace repo metadata

Usage:
    python import_schemas.py                   # Fetch new schemas
    python import_schemas.py --update          # Update all schemas
    python import_schemas.py --api replicate   # Fetch only Replicate
    python import_schemas.py --api falai       # Fetch only Fal.ai
    python import_schemas.py --api huggingface # Fetch only HuggingFace

Schemas are saved to the local schemas/ folder:
- schemas/Replicate/
- schemas/FalAi/
- schemas/HuggingFace/
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Import YAML for configuration
import yaml

# Get the package directory
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def format_json_file(file_path):
    """Format a JSON file with proper indentation."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Add run_count for tracking
            if isinstance(data, dict):
                data["run_count"] = data.get("run_count", 0)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except json.JSONDecodeError:
        print(f"Error: {file_path} contains invalid JSON")
        return False
    except IOError:
        print(f"Error: Could not read or write to {file_path}")
        return False


def format_json_files_in_directory(directory):
    """Format all JSON files in a directory."""
    if not os.path.exists(directory):
        return 0
    
    count = 0
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            if format_json_file(file_path):
                count += 1
    return count


def get_schemas_directory(api_name: str) -> str:
    """Get the local schemas directory for an API."""
    return os.path.join(PACKAGE_DIR, "schemas", api_name)


def get_config_file_path() -> str:
    """Get the path to the configuration file (YAML preferred, fallback to JSON)."""
    yaml_path = os.path.join(PACKAGE_DIR, "supported_models.yaml")
    json_path = os.path.join(PACKAGE_DIR, "supported_models.json")
    
    if os.path.exists(yaml_path):
        return yaml_path
    elif os.path.exists(json_path):
        return json_path
    else:
        return yaml_path  # Return YAML path even if it doesn't exist (for error message)


def load_config(config_file: str) -> dict:
    """
    Load configuration from YAML or JSON file.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_file}")
        return {}
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        print(f"Error: Could not parse {config_file}: {e}")
        return {}


def get_supported_models(config_file: str, api_name: str = None) -> list:
    """
    Load supported models from configuration file.
    
    Args:
        config_file: Path to the configuration file
        api_name: Optional API name to filter models ('replicate', 'falai', 'huggingface')
        
    Returns:
        List of model identifiers
    """
    config = load_config(config_file)
    
    if not config:
        return []
    
    if api_name:
        # Return models for specific API
        api_config = config.get(api_name, {})
        
        # Handle new YAML format (models as dict keys) or old JSON format (models as list)
        models_data = api_config.get("models", {})
        if isinstance(models_data, dict):
            # YAML format: models is a dict with model_id as keys
            return list(models_data.keys())
        elif isinstance(models_data, list):
            # Legacy JSON format: models is a list
            return models_data
        else:
            return []
    else:
        # Return all models combined
        all_models = []
        
        # Replicate models
        replicate_config = config.get("replicate", {})
        replicate_models = replicate_config.get("models", {})
        if isinstance(replicate_models, dict):
            all_models.extend(list(replicate_models.keys()))
        else:
            all_models.extend(replicate_models)
        
        # Fal.ai models
        falai_config = config.get("falai", {})
        falai_models = falai_config.get("models", {})
        if isinstance(falai_models, dict):
            all_models.extend(list(falai_models.keys()))
        else:
            all_models.extend(falai_models)
        
        # Legacy models (top-level)
        legacy_models = config.get("models", [])
        all_models.extend(legacy_models)
        
        return all_models


def update_replicate_schemas(update: bool = False) -> int:
    """Update schemas from Replicate API."""
    print("\n=== Updating Replicate Schemas ===")
    
    try:
        import replicate
    except ImportError:
        print("Error: replicate package not installed. Run: pip install replicate")
        return 0
    
    schemas_dir = get_schemas_directory("Replicate")
    if not schemas_dir:
        print("Error: Could not find Replicate schemas directory")
        return 0
    
    os.makedirs(schemas_dir, exist_ok=True)
    
    config_file = get_config_file_path()
    models = get_supported_models(config_file, "replicate")
    if not models:
        print(f"Warning: No Replicate models found in {config_file}")
        return 0
    
    existing_schemas = set(os.listdir(schemas_dir)) if os.path.exists(schemas_dir) else set()
    updated_count = 0
    
    for model in models:
        if not isinstance(model, str):
            continue
            
        schema_filename = f"{model.replace('/', '_')}.json"
        schema_path = os.path.join(schemas_dir, schema_filename)

        if update or schema_filename not in existing_schemas:
            try:
                m = replicate.models.get(model)
                with open(schema_path, "w", encoding="utf-8") as f:
                    f.write(m.json())
                print(f"  {'Updated' if update else 'Added'}: {model}")
                updated_count += 1
            except Exception as e:
                print(f"  Error fetching {model}: {str(e)}")
                continue
    
    # Format all JSON files
    formatted = format_json_files_in_directory(schemas_dir)
    print(f"Formatted {formatted} schema files")
    
    return updated_count


def update_falai_schemas(update: bool = False) -> int:
    """Update schemas from Fal.ai API."""
    print("\n=== Updating Fal.ai Schemas ===")
    
    schemas_dir = get_schemas_directory("FalAi")
    if not schemas_dir:
        print("Error: Could not find Fal.ai schemas directory")
        return 0
    
    os.makedirs(schemas_dir, exist_ok=True)
    
    config_file = get_config_file_path()
    models = get_supported_models(config_file, "falai")
    if not models:
        # Try legacy format
        all_models = get_supported_models(config_file)
        # Filter to only fal-ai models
        models = [m for m in all_models if isinstance(m, str) and m.startswith("fal-ai/")]
    
    if not models:
        print(f"Warning: No Fal.ai models found in {config_file}")
        return 0
    
    existing_schemas = set(os.listdir(schemas_dir)) if os.path.exists(schemas_dir) else set()
    updated_count = 0
    
    for model in models:
        if not isinstance(model, str):
            continue
            
        # Fal.ai uses endpoint_id format with slashes
        # e.g., "fal-ai/seedvr/upscale/image"
        # Convert to filename-friendly format
        schema_filename = f"{model.replace('/', '_').replace('-', '_')}.json"
        schema_path = os.path.join(schemas_dir, schema_filename)

        if update or schema_filename not in existing_schemas:
            try:
                # Fetch schema from FAL.ai API
                endpoint_id = model
                url = f"https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={endpoint_id}"
                
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as response:
                    schema_data = response.read().decode("utf-8")
                
                with open(schema_path, "w", encoding="utf-8") as f:
                    f.write(schema_data)
                print(f"  {'Updated' if update else 'Added'}: {model}")
                updated_count += 1
            except urllib.error.URLError as e:
                print(f"  Error fetching {model}: {str(e)}")
                continue
            except Exception as e:
                print(f"  Error processing {model}: {str(e)}")
                continue
    
    # Format all JSON files
    formatted = format_json_files_in_directory(schemas_dir)
    print(f"Formatted {formatted} schema files")
    
    return updated_count


def get_supported_repos(config_file: str) -> list:
    """
    Load supported HuggingFace repos from configuration (huggingface.repos section).
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        List of repo identifiers
    """
    config = load_config(config_file)
    
    if not config:
        return []
    
    hf_config = config.get("huggingface", {})
    repos = hf_config.get("repos", [])
    
    # Handle new YAML format (repos as dict keys) or old format (repos as list of strings/dicts)
    result = []
    for repo in repos:
        if isinstance(repo, dict):
            # YAML format: repos is a list of dicts with 'id' key
            result.append(repo.get("id", ""))
        elif isinstance(repo, str):
            # Legacy format: repos is a list of strings
            result.append(repo)
    
    return [r for r in result if r]  # Filter out empty strings


def update_huggingface_schemas(update: bool = False) -> int:
    """Update schemas (repo metadata) from HuggingFace API."""
    print("\n=== Updating HuggingFace Schemas ===")
    
    schemas_dir = get_schemas_directory("HuggingFace")
    os.makedirs(schemas_dir, exist_ok=True)
    
    config_file = get_config_file_path()
    repos = get_supported_repos(config_file)
    if not repos:
        print(f"Warning: No HuggingFace repos found in {config_file}")
        return 0
    
    try:
        from huggingface_hub import HfApi, login
        from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
    except ImportError:
        print("Warning: huggingface_hub not installed. HF_TOKEN will not work.")
        print("Run: pip install huggingface_hub")
        HF_AVAILABLE = False
        HfApi = None
    else:
        HF_AVAILABLE = True
    
    # Get HF token if available
    hf_token = os.environ.get("HF_TOKEN")
    api = None
    if HF_AVAILABLE and hf_token:
        try:
            login(token=hf_token)
            api = HfApi()
        except Exception as e:
            print(f"Warning: Could not authenticate with HuggingFace: {e}")
    
    existing_schemas = set(os.listdir(schemas_dir)) if os.path.exists(schemas_dir) else set()
    updated_count = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for repo_id in repos:
        if not isinstance(repo_id, str):
            continue
        
        # Convert repo_id to filename: "renderartist/Model" -> "renderartist_Model.json"
        schema_filename = f"{repo_id.replace('/', '_')}.json"
        schema_path = os.path.join(schemas_dir, schema_filename)

        if update or schema_filename not in existing_schemas:
            try:
                if api:
                    # Get repo info
                    repo_info = api.repo_info(repo_id)
                    
                    # List all .safetensors files
                    files = api.list_repo_files(repo_id=repo_id, revision="main")
                    safetensors = [f for f in files if f.endswith(".safetensors")]
                    safetensors.sort()
                    
                    # Build model entries with download URLs
                    models = []
                    for filename in safetensors:
                        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
                        models.append({
                            "filename": filename,
                            "url": url,
                            "path": filename
                        })
                    
                    # Create schema data
                    schema_data = {
                        "repo_id": repo_id,
                        "type": "huggingface_repo",
                        "repo_type": getattr(repo_info, 'repo_type', 'model'),
                        "models": models,
                        "metadata": {
                            "sha": getattr(repo_info, 'sha', None),
                            "downloads": getattr(repo_info, 'downloads', None),
                            "likes": getattr(repo_info, 'likes', None),
                            "tags": getattr(repo_info, 'tags', [])
                        },
                        "fetched_at": now
                    }
                else:
                    # Create placeholder schema if HF not available
                    schema_data = {
                        "repo_id": repo_id,
                        "type": "huggingface_repo",
                        "models": [],
                        "error": "huggingface_hub not available or HF_TOKEN not set",
                        "fetched_at": now
                    }
                
                with open(schema_path, "w", encoding="utf-8") as f:
                    json.dump(schema_data, f, indent=4, ensure_ascii=False)
                
                print(f"  {'Updated' if update else 'Added'}: {repo_id} ({len(schema_data.get('models', []))} models)")
                updated_count += 1
                
            except (RepositoryNotFoundError, GatedRepoError) as e:
                print(f"  Error accessing {repo_id}: {str(e)}")
                continue
            except Exception as e:
                print(f"  Error processing {repo_id}: {str(e)}")
                continue
    
    return updated_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import model schemas for ComfyUI-API-DockerCPU"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update all schemas, not just new ones"
    )
    parser.add_argument(
        "--api",
        choices=["replicate", "falai", "huggingface", "all"],
        default="all",
        help="Which API to update (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ComfyUI-API-DockerCPU Schema Import")
    print("=" * 60)
    
    config_file = get_config_file_path()
    print(f"Using configuration: {config_file}")
    
    total_updated = 0
    
    if args.api in ["replicate", "all"]:
        count = update_replicate_schemas(update=args.update)
        total_updated += count
        print(f"  Replicate: {count} schemas processed")
    
    if args.api in ["falai", "all"]:
        count = update_falai_schemas(update=args.update)
        total_updated += count
        print(f"  Fal.ai: {count} schemas processed")
    
    if args.api in ["huggingface", "all"]:
        count = update_huggingface_schemas(update=args.update)
        total_updated += count
        print(f"  HuggingFace: {count} repos processed")
    
    print("\n" + "=" * 60)
    print(f"Complete: {total_updated} schemas processed")
    print(f"Schemas saved to: {os.path.join(PACKAGE_DIR, 'schemas')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
