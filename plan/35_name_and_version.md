# Plan: Extract `name_and_version()` Function

## Function Overview
**Function Name**: `name_and_version()`
**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 279-300)
- `API/HuggingFace/schema_to_node.py` (lines 201-226)
- `API/Replicate/schema_to_node.py` (lines 363-378)

**Target Location**: Keep separate (API-specific implementations)

## Current Implementations (Different per API)

### FalAi Version
```python
def name_and_version(schema: Dict) -> tuple:
    """
    Extract model name and node name from Fal.ai schema.
    
    Args:
        schema: Fal.ai OpenAPI schema
        
    Returns:
        Tuple of (fal_model, node_name)
    """
    # Try x-fal-metadata endpointId first (Fal.ai specific)
    endpoint_id = schema.get("info", {}).get("x-fal-metadata", {}).get("endpointId")
    
    if not endpoint_id:
        # Fallback to owner/name format
        author = schema.get("owner", "")
        name = schema.get("name", "")
        endpoint_id = f"{author}/{name}"
    
    fal_model = endpoint_id
    node_name = f"Fal AI {endpoint_id}"
    return fal_model, node_name
```

### HuggingFace Version
```python
def name_and_version(schema: Dict) -> tuple:
    """
    Extract model name and node name from HuggingFace schema.
    
    Args:
        schema: HuggingFace model schema
        
    Returns:
        Tuple of (model_name, node_name)
    """
    # Try different schema formats
    model_id = schema.get("model_id", "")
    
    if not model_id:
        # Try owner/name format
        owner = schema.get("owner", "")
        name = schema.get("name", "")
        model_id = f"{owner}/{name}" if owner else name
    
    # Get version if available
    version = schema.get("version", "latest")
    
    hf_model = model_id
    node_name = f"HF {model_id}"
    
    return hf_model, node_name
```

### Replicate Version
```python
def name_and_version(schema: Dict) -> tuple:
    """
    Extract model name and node name from schema.
    
    Args:
        schema: Replicate OpenAPI schema
        
    Returns:
        Tuple of (replicate_model, node_name)
    """
    author = schema["owner"]
    name = schema["name"]
    version = schema["latest_version"]["id"]
    replicate_model = f"{author}/{name}:{version}"
    node_name = f"Replicate {author}/{name}"
    return replicate_model, node_name
```

## Why Keep Separate
- **Duplication Level**: Different implementations per API
- **Risk Level**: N/A (API-specific logic)
- **Impact**: N/A (API-specific logic)
- **Lines Saved**: 0 (cannot be unified)

## Implementation Steps

### Step 1: Keep Functions Separate
The `name_and_version()` function has different implementations for each API:
- FalAi: Uses `x-fal-metadata.endpointId` or `owner/name` format
- HuggingFace: Uses `model_id` or `owner/name` format
- Replicate: Uses `owner/name:version` format

These differences are API-specific and cannot be easily unified without adding complexity.

### Step 2: Document API-Specific Behavior
Each API should document its own `name_and_version()` implementation clearly.

## Testing Checklist

- [ ] Verify FalAi version extracts endpointId correctly
- [ ] Verify FalAi version falls back to owner/name format
- [ ] Verify HuggingFace version extracts model_id correctly
- [ ] Verify HuggingFace version falls back to owner/name format
- [ ] Verify Replicate version extracts owner/name:version correctly
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
