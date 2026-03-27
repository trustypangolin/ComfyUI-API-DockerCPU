"""
Schema validation tests for ComfyUI-API-DockerCPU

Tests that can be run outside of ComfyUI to validate:
- Schema loading
- Input type conversion
- Return type extraction
- Node class creation

Note: Some tests require ComfyUI dependencies (torch) which are only
available in the ComfyUI environment. These tests will be skipped
gracefully if dependencies are not available.
"""

import json
import os
import sys
from typing import Dict

# Add project root to sys.path for package imports
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# Check if ComfyUI dependencies are available
COMFYUI_AVAILABLE = False
try:
    import torch
    COMFYUI_AVAILABLE = True
except ImportError:
    pass


def get_schemas_dir(api_name: str) -> str:
    """Get the schemas directory for an API."""
    # Use local schemas folder
    local_dirs = {
        "Replicate": os.path.join(PACKAGE_DIR, "schemas", "Replicate"),
        "FalAi": os.path.join(PACKAGE_DIR, "schemas", "FalAi"),
        "HuggingFace": os.path.join(PACKAGE_DIR, "schemas", "HuggingFace"),
    }
    
    # Normalize path
    path = local_dirs.get(api_name, "")
    return os.path.normpath(path)


def load_schema(api_name: str, schema_file: str) -> Dict:
    """Load a schema file."""
    schemas_dir = get_schemas_dir(api_name)
    schema_path = os.path.join(schemas_dir, schema_file)
    
    if not os.path.exists(schema_path):
        return None
    
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_replicate_schemas():
    """Test Replicate schema loading and conversion."""
    print("\n=== Testing Replicate Schemas ===")
    
    schemas_dir = get_schemas_dir("Replicate")
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: Replicate schemas directory not found: {schemas_dir}")
        print("Run 'python import_schemas.py --api replicate' to fetch schemas")
        return
    
    # Import from package (respects package structure)
    # This may fail if ComfyUI dependencies are not available
    try:
        from API.Replicate.schema_to_node import schema_to_comfyui_input_types, get_return_type, name_and_version
    except ImportError as e:
        if "torch" in str(e):
            print("Note: torch not available, skipping schema_to_node import test")
            print("(This is expected outside of ComfyUI environment)")
            return
        raise
    
    schema_files = [f for f in os.listdir(schemas_dir) if f.endswith(".json")]
    
    if not schema_files:
        print("No schema files found")
        return
    
    print(f"Found {len(schema_files)} schema files")
    
    for schema_file in sorted(schema_files):
        try:
            schema = load_schema("Replicate", schema_file)
            if not schema:
                continue
            
            # Test name extraction
            model_name, node_name = name_and_version(schema)
            print(f"\n{'='*60}")
            print(f"Schema: {schema_file}")
            print(f"{'='*60}")
            print(f"Model: {model_name}")
            print(f"Node: {node_name}")
            
            # Test input types - show detailed inputs and parameters
            input_types = schema_to_comfyui_input_types(schema)
            
            # Helper function to display a parameter
            def display_param(name, config, required_label):
                if isinstance(config, tuple) and len(config) == 2:
                    param_type, param_dict = config
                    if isinstance(param_dict, dict):
                        default = param_dict.get("default", "N/A")
                        desc = param_dict.get("description", "")
                        max_val = param_dict.get("max")
                        options = param_dict.get("options", [])
                        opts_str = ""
                        if options:
                            opts_str = f" (options: {options[:5]}{'...' if len(options) > 5 else ''})"
                        max_str = f" [max: {max_val}]" if max_val is not None else ""
                        desc_str = f" - {desc[:60]}{'...' if len(desc) > 60 else ''}" if desc else ""
                        print(f"    • {name}: {param_type}{opts_str}{max_str} [{required_label}, default: {default}]{desc_str}")
                    else:
                        print(f"    • {name}: {config}")
                elif isinstance(config, dict):
                    param_type = config.get("type", "unknown")
                    default = config.get("default", "N/A")
                    max_val = config.get("max")
                    max_str = f" [max: {max_val}]" if max_val is not None else ""
                    print(f"    • {name}: {param_type}{max_str} [{required_label}, default: {default}]")
                else:
                    print(f"    • {name}: {config}")
            
            # Separate INPUTS (IMAGE, AUDIO, VIDEO) from PARAMETERS (STRING, INT, FLOAT, BOOLEAN)
            required = input_types.get("required", {})
            
            image_inputs = {}
            audio_inputs = {}
            video_inputs = {}
            other_params = {}
            
            for param_name, param_config in required.items():
                if isinstance(param_config, tuple) and len(param_config) == 2:
                    param_type = param_config[0]
                    if isinstance(param_type, tuple):
                        param_type = param_type[0] if param_type else "STRING"
                    if param_type == "IMAGE":
                        image_inputs[param_name] = param_config
                    elif param_type == "AUDIO":
                        audio_inputs[param_name] = param_config
                    elif param_type == "VIDEO":
                        video_inputs[param_name] = param_config
                    else:
                        other_params[param_name] = param_config
                else:
                    other_params[param_name] = param_config
            
            # Display INPUTS section
            if image_inputs or audio_inputs or video_inputs:
                print(f"\n📥 INPUTS:")
                print("-" * 40)
                if image_inputs:
                    print(f"  📷 IMAGE inputs ({len(image_inputs)} slots):")
                    for param_name, param_config in sorted(image_inputs.items()):
                        display_param(param_name, param_config, "input")
                if audio_inputs:
                    print(f"  🔊 AUDIO inputs ({len(audio_inputs)} slots):")
                    for param_name, param_config in sorted(audio_inputs.items()):
                        display_param(param_name, param_config, "input")
                if video_inputs:
                    print(f"  🎬 VIDEO inputs ({len(video_inputs)} slots):")
                    for param_name, param_config in sorted(video_inputs.items()):
                        display_param(param_name, param_config, "input")
            
            # Display PARAMETERS section
            if other_params:
                print(f"\n⚙️ PARAMETERS:")
                print("-" * 40)
                for param_name, param_config in sorted(other_params.items()):
                    display_param(param_name, param_config, "parameter")
            
            # Test return types - show outputs
            print(f"\n📤 OUTPUTS:")
            print("-" * 40)
            return_type = get_return_type(schema)
            if isinstance(return_type, dict):
                for output_name, output_type in return_type.items():
                    print(f"    • {output_name}: {output_type}")
            else:
                print(f"    • {return_type}")
            
        except Exception as e:
            print(f"Error processing {schema_file}: {e}")


def test_falai_schemas():
    """Test FalAi schema loading and conversion."""
    print("\n=== Testing FalAi Schemas ===")
    
    schemas_dir = get_schemas_dir("FalAi")
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: FalAi schemas directory not found: {schemas_dir}")
        print("Run 'python import_schemas.py --api falai' to fetch schemas")
        return
    
    # Import from package (respects package structure)
    # This may fail if ComfyUI dependencies are not available
    try:
        from API.FalAi.schema_to_node import schema_to_comfyui_input_types, get_return_type, name_and_version
    except ImportError as e:
        if "torch" in str(e):
            print("Note: torch not available, skipping schema_to_node import test")
            print("(This is expected outside of ComfyUI environment)")
            return
        raise
    
    schema_files = [f for f in os.listdir(schemas_dir) if f.endswith(".json")]
    
    if not schema_files:
        print("No schema files found")
        return
    
    print(f"Found {len(schema_files)} schema files")
    
    for schema_file in sorted(schema_files):
        try:
            schema = load_schema("FalAi", schema_file)
            if not schema:
                continue
            
            # Test name extraction
            model_name, node_name = name_and_version(schema)
            print(f"\n{'='*60}")
            print(f"Schema: {schema_file}")
            print(f"{'='*60}")
            print(f"Model: {model_name}")
            print(f"Node: {node_name}")
            
            # Test input types - show detailed inputs and parameters
            input_types = schema_to_comfyui_input_types(schema)
            
            # Helper function to display a parameter
            def display_param(name, config, required_label):
                if isinstance(config, tuple) and len(config) == 2:
                    param_type, param_dict = config
                    if isinstance(param_dict, dict):
                        default = param_dict.get("default", "N/A")
                        desc = param_dict.get("description", "")
                        max_val = param_dict.get("max")
                        options = param_dict.get("options", [])
                        opts_str = ""
                        if options:
                            opts_str = f" (options: {options[:5]}{'...' if len(options) > 5 else ''})"
                        max_str = f" [max: {max_val}]" if max_val is not None else ""
                        desc_str = f" - {desc[:60]}{'...' if len(desc) > 60 else ''}" if desc else ""
                        print(f"    • {name}: {param_type}{opts_str}{max_str} [{required_label}, default: {default}]{desc_str}")
                    else:
                        print(f"    • {name}: {config}")
                elif isinstance(config, dict):
                    param_type = config.get("type", "unknown")
                    default = config.get("default", "N/A")
                    max_val = config.get("max")
                    max_str = f" [max: {max_val}]" if max_val is not None else ""
                    print(f"    • {name}: {param_type}{max_str} [{required_label}, default: {default}]")
                else:
                    print(f"    • {name}: {config}")
            
            # Separate INPUTS (IMAGE, AUDIO, VIDEO) from PARAMETERS (STRING, INT, FLOAT, BOOLEAN)
            required = input_types.get("required", {})
            
            image_inputs = {}
            audio_inputs = {}
            video_inputs = {}
            other_params = {}
            
            for param_name, param_config in required.items():
                if isinstance(param_config, tuple) and len(param_config) == 2:
                    param_type = param_config[0]
                    if isinstance(param_type, tuple):
                        param_type = param_type[0] if param_type else "STRING"
                    if param_type == "IMAGE":
                        image_inputs[param_name] = param_config
                    elif param_type == "AUDIO":
                        audio_inputs[param_name] = param_config
                    elif param_type == "VIDEO":
                        video_inputs[param_name] = param_config
                    else:
                        other_params[param_name] = param_config
                else:
                    other_params[param_name] = param_config
            
            # Display INPUTS section
            if image_inputs or audio_inputs or video_inputs:
                print(f"\n📥 INPUTS:")
                print("-" * 40)
                if image_inputs:
                    print(f"  📷 IMAGE inputs ({len(image_inputs)} slots):")
                    for param_name, param_config in sorted(image_inputs.items()):
                        display_param(param_name, param_config, "input")
                if audio_inputs:
                    print(f"  🔊 AUDIO inputs ({len(audio_inputs)} slots):")
                    for param_name, param_config in sorted(audio_inputs.items()):
                        display_param(param_name, param_config, "input")
                if video_inputs:
                    print(f"  🎬 VIDEO inputs ({len(video_inputs)} slots):")
                    for param_name, param_config in sorted(video_inputs.items()):
                        display_param(param_name, param_config, "input")
            
            # Display PARAMETERS section
            if other_params:
                print(f"\n⚙️ PARAMETERS:")
                print("-" * 40)
                for param_name, param_config in sorted(other_params.items()):
                    display_param(param_name, param_config, "parameter")
            
            # Test return types - show outputs
            print(f"\n📤 OUTPUTS:")
            print("-" * 40)
            return_type = get_return_type(schema)
            if isinstance(return_type, dict):
                for output_name, output_type in return_type.items():
                    print(f"    • {output_name}: {output_type}")
            else:
                print(f"    • {return_type}")
            
        except Exception as e:
            print(f"Error processing {schema_file}: {e}")


def test_huggingface_schemas():
    """Test HuggingFace schema/repo metadata loading."""
    print("\n=== Testing HuggingFace Schemas ===")
    
    schemas_dir = get_schemas_dir("HuggingFace")
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: HuggingFace schemas directory not found: {schemas_dir}")
        print("Run 'python import_schemas.py --api huggingface' to fetch schemas")
        return
    
    schema_files = [f for f in os.listdir(schemas_dir) if f.endswith(".json")]
    
    if not schema_files:
        print("No schema files found")
        return
    
    print(f"Found {len(schema_files)} schema files")
    
    for schema_file in sorted(schema_files):
        try:
            schema = load_schema("HuggingFace", schema_file)
            if not schema:
                continue
            
            repo_id = schema.get("id", schema_file.replace(".json", "").replace("_", "/"))
            
            print(f"\n{'='*60}")
            print(f"Schema: {schema_file}")
            print(f"{'='*60}")
            print(f"Repo ID: {repo_id}")
            print(f"Name: {schema.get('name', 'N/A')}")
            print(f"Private: {schema.get('private', False)}")
            print(f"Downloads: {schema.get('downloads', 0)}")
            
            # Show inputs/parameters from schema
            inputs = schema.get("inputs", {})
            if inputs:
                print(f"\n📥 INPUTS/PARAMETERS:")
                print("-" * 40)
                for param_name, param_config in inputs.items():
                    if isinstance(param_config, dict):
                        param_type = param_config.get("type", "unknown")
                        required = param_config.get("required", False)
                        default = param_config.get("default", "N/A")
                        options = param_config.get("options", [])
                        source = "required" if required else "optional"
                        if options:
                            print(f"    • {param_name}: {param_type} [{source}] (options: {options[:5]}{'...' if len(options) > 5 else ''})")
                        else:
                            print(f"    • {param_name}: {param_type} [{source}] [default: {default}]")
                    else:
                        print(f"    • {param_name}: {param_config}")
            
            # Show outputs
            outputs = schema.get("outputs", [])
            if outputs:
                print(f"\n📤 OUTPUTS:")
                print("-" * 40)
                for output in outputs:
                    if isinstance(output, dict):
                        print(f"    • {output.get('name', 'unnamed')}: {output.get('type', 'unknown')}")
                    else:
                        print(f"    • {output}")
            
            # Show model files
            models = schema.get("models", [])
            if models:
                print(f"\n📁 MODEL FILES:")
                print("-" * 40)
                safetensors = [m.get("filename", m.get("path", "")) for m in models[:5]]
                print(f"  {safetensors}")
                if len(models) > 5:
                    print(f"  ... and {len(models) - 5} more files")
                
        except Exception as e:
            print(f"Error processing {schema_file}: {e}")
    
    # Try to import the node module if possible
    try:
        from API.HuggingFace.node import load_schema_for_repo, load_all_schemas
        
        print("\n  Node module functions available:")
        print("    - load_schema_for_repo(repo_id)")
        print("    - load_all_schemas()")
        
    except ImportError as e:
        print(f"\n  Note: Full node module requires ComfyUI environment: {e}")


def test_common_utils():
    """Test common utility functions."""
    print("\n=== Testing Common Utilities ===")
    
    try:
        from common.utils import (
            image_to_base64,
            base64_to_tensor,
            convert_to_json_serializable,
            format_value_for_log,
        )
        
        print("Common utilities imported successfully")
        
        # Test JSON serialization
        import torch
        test_data = {
            "tensor": torch.randn(1, 3, 64, 64),
            "string": "test",
            "number": 42,
        }
        
        serialized = convert_to_json_serializable(test_data)
        print(f"JSON serialization test: {type(serialized)}")
        
        # Test log formatting
        formatted = format_value_for_log("data:image/png;base64,abc123...")
        print(f"Log formatting test: {formatted}")
        
    except ImportError as e:
        print(f"Could not import common utils: {e}")
    except Exception as e:
        print(f"Error testing utilities: {e}")


def test_node_creation():
    """Test that nodes can be created."""
    print("\n=== Testing Node Creation ===")
    
    # Test Replicate node creation
    schemas_dir = get_schemas_dir("Replicate")
    if os.path.exists(schemas_dir):
        try:
            from API.Replicate.node import create_comfyui_node
            schema_files = [f for f in os.listdir(schemas_dir) if f.endswith(".json")]
            
            if schema_files:
                schema = load_schema("Replicate", schema_files[0])
                if schema:
                    node_name, node_class = create_comfyui_node(schema)
                    print(f"Replicate node created: {node_name}")
                    
                    # Check INPUT_TYPES
                    input_types = node_class.INPUT_TYPES()
                    print(f"  INPUT_TYPES: {list(input_types.keys())}")
                    
                    # Check RETURN_TYPES
                    print(f"  RETURN_TYPES: {node_class.RETURN_TYPES}")
                    print(f"  RETURN_NAMES: {node_class.RETURN_NAMES}")
                    
        except ImportError as e:
            print(f"Could not import Replicate node module: {e}")
        except Exception as e:
            print(f"Error creating Replicate node: {e}")
    
    # Test HuggingFace nodes
    try:
        from API.HuggingFace.node import NODE_CLASS_MAPPINGS
        print(f"\nHuggingFace nodes available: {list(NODE_CLASS_MAPPINGS.keys())}")
        
        for node_name, node_class in NODE_CLASS_MAPPINGS.items():
            print(f"  {node_name}:")
            print(f"    Category: {node_class.CATEGORY}")
            print(f"    Function: {node_class.FUNCTION}")
            
    except ImportError as e:
        print(f"Could not import HuggingFace nodes: {e}")
    except Exception as e:
        print(f"Error testing HuggingFace nodes: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ComfyUI-API-DockerCPU Schema Tests")
    print("=" * 60)
    
    test_replicate_schemas()
    test_falai_schemas()
    test_huggingface_schemas()
    test_common_utils()
    test_node_creation()
    
    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
