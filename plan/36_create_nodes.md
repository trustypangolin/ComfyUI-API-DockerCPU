# Plan: Extract `create_nodes()` Function

## Function Overview
**Function Name**: `create_nodes()`
**Current Location**: 
- `API/FalAi/node.py` (lines 372-405)
- `API/HuggingFace/node.py` (lines 462-475)
- `API/Replicate/node.py` (lines 433-468)

**Target Location**: Keep separate (API-specific implementations)

## Current Implementations (Different per API)

### FalAi Version
```python
def create_nodes(schemas_dir: str = None) -> Dict[str, type]:
    """
    Create all ComfyUI nodes from schema files.
    
    Args:
        schemas_dir: Directory containing JSON schema files.
                    If None, uses the default schemas directory.
    
    Returns:
        Dictionary mapping node names to node classes
    """
    if schemas_dir is None:
        # Get the package directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Use local schemas folder: package_dir/schemas/FalAi/
        schemas_dir = os.path.join(package_dir, "schemas", "FalAi")
    
    nodes = {}
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: Schemas directory not found: {schemas_dir}")
        return nodes
    
    for schema_file in os.listdir(schemas_dir):
        if schema_file.endswith(".json"):
            try:
                with open(os.path.join(schemas_dir, schema_file), "r", encoding="utf-8") as f:
                    schema = json.load(f)
                node_name, node_class = create_comfyui_node(schema)
                nodes[node_name] = node_class
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")
    
    return nodes
```

### HuggingFace Version
```python
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
```

### Replicate Version
```python
def create_nodes(schemas_dir: str = None) -> Dict[str, type]:
    """
    Create all ComfyUI nodes from schema files.
    
    Args:
        schemas_dir: Directory containing JSON schema files.
                    If None, uses the default schemas directory.
    
    Returns:
        Dictionary mapping node names to node classes
    """
    import base64
    
    if schemas_dir is None:
        # Get the package directory
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Use local schemas folder: package_dir/schemas/Replicate/
        schemas_dir = os.path.join(package_dir, "schemas", "Replicate")
    
    nodes = {}
    
    if not os.path.exists(schemas_dir):
        print(f"Warning: Schemas directory not found: {schemas_dir}")
        return nodes
    
    for schema_file in os.listdir(schemas_dir):
        if schema_file.endswith(".json"):
            try:
                with open(os.path.join(schemas_dir, schema_file), "r", encoding="utf-8") as f:
                    schema = json.load(f)
                node_name, node_class = create_comfyui_node(schema)
                nodes[node_name] = node_class
            except Exception as e:
                print(f"Error loading schema {schema_file}: {e}")
    
    return nodes
```

## Why Keep Separate
- **Duplication Level**: Different implementations per API
- **Risk Level**: N/A (API-specific logic)
- **Impact**: N/A (API-specific logic)
- **Lines Saved**: 0 (cannot be unified)

## Implementation Steps

### Step 1: Keep Functions Separate
The `create_nodes()` function has different implementations for each API:
- FalAi: Loads schemas from `schemas/FalAi/` directory
- HuggingFace: Returns utility nodes (no schema loading)
- Replicate: Loads schemas from `schemas/Replicate/` directory

These differences are API-specific and cannot be easily unified without adding complexity.

### Step 2: Document API-Specific Behavior
Each API should document its own `create_nodes()` implementation clearly.

## Testing Checklist

- [ ] Verify FalAi version loads schemas from correct directory
- [ ] Verify FalAi version creates nodes correctly
- [ ] Verify HuggingFace version returns utility nodes
- [ ] Verify Replicate version loads schemas from correct directory
- [ ] Verify Replicate version creates nodes correctly
- [ ] Test with FalAi API
- [ ] Test with HuggingFace API
- [ ] Test with Replicate API
- [ ] Run full test suite for all APIs

## Dependencies
- None (API-specific implementations)

## Rollback Plan
No changes needed (functions are API-specific).

## Estimated Time
- Implementation: 0 minutes (keep separate)
- Testing: 15 minutes
- Total: 15 minutes
