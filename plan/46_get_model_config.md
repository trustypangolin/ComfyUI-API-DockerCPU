# Plan: Extract `get_model_config()` and `get_standard_parameters()` Functions

## Functions Overview
**Functions**:
1. `get_model_config()`
2. `get_standard_parameters()`

**Current Location**: 
- `common/config_loader.py` (already exists)

**Target Location**: `common/config_loader.py` (already there, just document it)

## Current Implementations (Already in common/config_loader.py)

The functions already exist in `common/config_loader.py` as part of the `ConfigLoader` class. They are used to get model configuration and standard parameters from the configuration files.

## Why Document
- **Duplication Level**: Already in common/config_loader.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Functions Exist
The functions already exist in `common/config_loader.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (functions are only in common/config_loader.py)

## Testing Checklist

- [ ] Verify `get_model_config()` returns correct config for model
- [ ] Verify `get_model_config()` returns None when not configured
- [ ] Verify `get_standard_parameters()` returns correct parameters for API
- [ ] Verify `get_standard_parameters()` returns empty dict when not configured
- [ ] Run full test suite for all APIs

## Dependencies
- None (standalone utility functions)

## Rollback Plan
No changes needed (functions already exist).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 10 minutes
- Total: 10 minutes
