# Plan: Extract Parameter Ordering Functions

## Functions Overview
**Functions**:
1. `get_parameter_order()`
2. `get_parameter_group()`
3. `sort_inputs_by_group_and_order()`

**Current Location**: 
- `API/FalAi/schema_to_node.py` (lines 363-464)
- `API/HuggingFace/schema_to_node.py` (lines 246-342)

**Target Location**: `common/schema_utils.py`

## Current Implementations (100% Identical)

### get_parameter_order()
```python
def get_parameter_order(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    schema_order: Optional[int] = None
) -> int:
    """
    Get sort order for a parameter.
    
    Order priority:
    1. Explicit order from config (-1 for system, 0+ for user params)
    2. Schema x-order if available
    3. Default order (100)
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration
        schema_order: x-order from schema
        
    Returns:
        Sort order (lower = earlier in list)
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'order' in param_config:
            return param_config['order']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'order' in input_config:
            return input_config['order']
    
    if schema_order is not None:
        return schema_order
    
    return 100
```

### get_parameter_group()
```python
def get_parameter_group(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get parameter group (system, basic, advanced).
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration
        
    Returns:
        Group name (default: "basic")
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'group' in param_config:
            return param_config['group']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'group' in input_config:
            return input_config['group']
    
    return "basic"
```

### sort_inputs_by_group_and_order()
```python
def sort_inputs_by_group_and_order(
    inputs: Dict[str, Any],
    model_config: Optional[Dict[str, Any]] = None,
    schema_order_map: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Sort inputs by group then by order.
    
    Group order: system (0), basic (1+), advanced (10+)
    
    Args:
        inputs: Dictionary of input definitions
        model_config: Model-specific configuration
        schema_order_map: Map of field names to x-order from schema
        
    Returns:
        Sorted dictionary
    """
    # Define group priority (lower = appears first)
    group_priority = {
        "system": 0,
        "basic": 1,
        "advanced": 2,
    }
    
    def get_sort_key(item):
        name, _ = item
        group = get_parameter_group(name, model_config)
        order = get_parameter_order(name, model_config, schema_order_map.get(name))
        group_ord = group_priority.get(group, 99)
        return (group_ord, order, name)
    
    sorted_items = sorted(inputs.items(), key=get_sort_key)
    return dict(sorted_items)
```

## Why Extract
- **Duplication Level**: 100% identical in FalAi & HuggingFace
- **Risk Level**: Very Low
- **Impact**: High (used in schema conversion for all models)
- **Lines Saved**: ~200 lines (100 lines × 2 files)

## Implementation Steps

### Step 1: Add to `common/schema_utils.py`
Add all three functions to `common/schema_utils.py` with enhanced documentation:

```python
def get_parameter_order(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None,
    schema_order: Optional[int] = None
) -> int:
    """
    Get sort order for a parameter.
    
    Order priority:
    1. Explicit order from config (-1 for system, 0+ for user params)
    2. Schema x-order if available
    3. Default order (100)
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration (from supported_models.yaml)
        schema_order: x-order from schema (if available)
        
    Returns:
        Sort order (lower = earlier in list)
        
    Examples:
        >>> config = {"parameters": {"seed": {"order": 0}}}
        >>> get_parameter_order("seed", config)
        0
        >>> get_parameter_order("prompt", config)
        100
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'order' in param_config:
            return param_config['order']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'order' in input_config:
            return input_config['order']
    
    if schema_order is not None:
        return schema_order
    
    return 100


def get_parameter_group(
    param_name: str,
    model_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get parameter group (system, basic, advanced).
    
    Args:
        param_name: Name of the parameter
        model_config: Model-specific configuration (from supported_models.yaml)
        
    Returns:
        Group name: "system", "basic", or "advanced" (default: "basic")
        
    Examples:
        >>> config = {"parameters": {"seed": {"group": "system"}}}
        >>> get_parameter_group("seed", config)
        'system'
        >>> get_parameter_group("prompt", config)
        'basic'
    """
    if model_config:
        params = model_config.get('parameters', {})
        param_config = params.get(param_name, {})
        if 'group' in param_config:
            return param_config['group']
        
        # Check inputs section for input fields
        inputs = model_config.get('inputs', {})
        input_config = inputs.get(param_name, {})
        if 'group' in input_config:
            return input_config['group']
    
    return "basic"


def sort_inputs_by_group_and_order(
    inputs: Dict[str, Any],
    model_config: Optional[Dict[str, Any]] = None,
    schema_order_map: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Sort inputs by group then by order.
    
    Group order: system (0), basic (1+), advanced (10+)
    
    Args:
        inputs: Dictionary of input definitions
        model_config: Model-specific configuration (from supported_models.yaml)
        schema_order_map: Map of field names to x-order from schema
        
    Returns:
        Sorted dictionary with inputs ordered by group and order
        
    Examples:
        >>> inputs = {"prompt": ..., "seed": ..., "steps": ...}
        >>> config = {"parameters": {"seed": {"group": "system", "order": 0}}}
        >>> sorted_inputs = sort_inputs_by_group_and_order(inputs, config)
        >>> list(sorted_inputs.keys())
        ['seed', 'prompt', 'steps']
    """
    # Define group priority (lower = appears first)
    group_priority = {
        "system": 0,
        "basic": 1,
        "advanced": 2,
    }
    
    def get_sort_key(item):
        name, _ = item
        group = get_parameter_group(name, model_config)
        order = get_parameter_order(name, model_config, schema_order_map.get(name))
        group_ord = group_priority.get(group, 99)
        return (group_ord, order, name)
    
    sorted_items = sorted(inputs.items(), key=get_sort_key)
    return dict(sorted_items)
```

### Step 2: Update `API/FalAi/schema_to_node.py`
- Remove the three function definitions (lines 363-464)
- Add import: `from common.schema_utils import get_parameter_order, get_parameter_group, sort_inputs_by_group_and_order`
- No other changes needed (function signatures are identical)

### Step 3: Update `API/HuggingFace/schema_to_node.py`
- Remove the three function definitions (lines 246-342)
- Add import: `from common.schema_utils import get_parameter_order, get_parameter_group, sort_inputs_by_group_and_order`
- No other changes needed (function signatures are identical)

## Testing Checklist

- [ ] Verify `get_parameter_order()` returns correct order from config
- [ ] Verify `get_parameter_order()` returns correct order from schema
- [ ] Verify `get_parameter_order()` returns default order (100) when not specified
- [ ] Verify `get_parameter_group()` returns correct group from config
- [ ] Verify `get_parameter_group()` returns "basic" when not specified
- [ ] Verify `sort_inputs_by_group_and_order()` sorts correctly by group
- [ ] Verify `sort_inputs_by_group_and_order()` sorts correctly by order within group
- [ ] Run tests for FalAi API
- [ ] Run tests for HuggingFace API
- [ ] Verify schema conversion still works correctly

## Dependencies
- `get_parameter_order()` and `get_parameter_group()` are used by `sort_inputs_by_group_and_order()`
- All three functions must be extracted together

## Rollback Plan
If issues arise, simply revert the changes and restore the original function definitions in each API file.

## Estimated Time
- Implementation: 15 minutes
- Testing: 20 minutes
- Total: 35 minutes
