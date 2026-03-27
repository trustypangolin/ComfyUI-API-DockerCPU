# Plan: Extract `ConfigLoader` Class

## Class Overview
**Class Name**: `ConfigLoader`
**Current Location**: 
- `common/config_loader.py` (already exists)

**Target Location**: `common/config_loader.py` (already there, just document it)

## Current Implementation (Already in common/config_loader.py)

The class already exists in `common/config_loader.py`. It provides methods for loading and accessing configuration from YAML files.

## Why Document
- **Duplication Level**: Already in common/config_loader.py
- **Risk Level**: None
- **Impact**: Low (already available)
- **Lines Saved**: 0 (already extracted)

## Implementation Steps

### Step 1: Verify Class Exists
The class already exists in `common/config_loader.py`. No changes needed.

### Step 2: Update API Files (if needed)
Check if any API files have duplicate implementations:
- None found (class is only in common/config_loader.py)

## Testing Checklist

- [ ] Verify `ConfigLoader` loads global_inputs.yaml correctly
- [ ] Verify `ConfigLoader` loads global_outputs.yaml correctly
- [ ] Verify `ConfigLoader` loads global_parameters.yaml correctly
- [ ] Verify `ConfigLoader` loads supported_models.yaml correctly
- [ ] Verify `ConfigLoader` provides correct methods for accessing config
- [ ] Run full test suite for all APIs

## Dependencies
- None (standalone utility class)

## Rollback Plan
No changes needed (class already exists).

## Estimated Time
- Implementation: 0 minutes (already done)
- Testing: 15 minutes
- Total: 15 minutes
