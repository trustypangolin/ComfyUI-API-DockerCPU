# Refactoring Overview: Common Functions Extraction

## Objective
Extract duplicated Python functions from three API implementations (FalAi, HuggingFace, Replicate) into common utility modules to reduce code duplication, improve maintainability, and ensure consistent behavior.

## Current State
- **FalAi**: `API/FalAi/node.py` (405 lines), `API/FalAi/schema_to_node.py` (908 lines)
- **HuggingFace**: `API/HuggingFace/node.py` (475 lines), `API/HuggingFace/schema_to_node.py` (556 lines)
- **Replicate**: `API/Replicate/node.py` (468 lines), `API/Replicate/schema_to_node.py` (1085 lines)
- **Common**: `common/utils.py` (249 lines), `common/type_mapping.py` (555 lines)

## Identified Duplication
- ~2000+ lines of duplicate or near-duplicate code across the three APIs
- 20+ functions that are identical or 80-99% similar
- Multiple opportunities for consolidation

## Refactoring Phases

### Phase 1: Schema Utilities (Quick Wins)
**Target Files**: `common/schema_utils.py`
**Functions**:
1. `is_type()` - 100% identical in all 3 APIs
2. `get_input_type_from_config()` - 100% identical in all 3 APIs
3. `get_parameter_order()` - 100% identical in FalAi & HuggingFace
4. `get_parameter_group()` - 100% identical in FalAi & HuggingFace
5. `sort_inputs_by_group_and_order()` - 100% identical in FalAi & HuggingFace
6. `get_output_name_with_alias()` - ~95% similar (API name differs)
7. `get_model_config_override()` - ~90% similar (API name differs)
8. `convert_to_comfyui_input_type()` - ~85% similar in FalAi & Replicate

**Risk Level**: Low
**Impact**: High
**Estimated Lines Saved**: ~400 lines

### Phase 2: Input/Output Handlers
**Target Files**: 
- `common/input_handlers.py`
- `common/output_handlers.py`

**Functions**:
1. `handle_array_inputs()` - 100% identical in FalAi & Replicate
2. `remove_falsey_optional_inputs()` - ~95% similar in FalAi & Replicate
3. `convert_input_images_to_base64()` - ~90% similar in FalAi & Replicate
4. `handle_image_output()` - 100% identical in FalAi & Replicate
5. `handle_audio_output()` - 100% identical in FalAi & Replicate
6. `_process_output()` - ~85% similar in FalAi & Replicate

**Risk Level**: Medium
**Impact**: High
**Estimated Lines Saved**: ~600 lines

### Phase 3: Utility Functions
**Target Files**: `common/utils.py` (enhance existing)
**Functions**:
1. `_image_to_base64()` - ~80% similar in FalAi & Replicate
2. `_audio_to_base64()` - ~80% similar in FalAi & Replicate
3. `_base64_to_tensor()` - ~85% similar in FalAi & Replicate

**Risk Level**: Medium
**Impact**: High
**Estimated Lines Saved**: ~300 lines

### Phase 4: Logging & Debug
**Target Files**:
- `common/logging_utils.py`
- `common/dry_run.py`
- `common/debug_utils.py`

**Functions**:
1. `_log_input()` - ~90% similar in FalAi & Replicate
2. `_dry_run_output()` - ~80% similar in FalAi & Replicate
3. `debug_schema_conversion()` - ~75% similar in FalAi & Replicate
4. `get_standard_parameters()` - 100% identical in FalAi & Replicate

**Risk Level**: Low
**Impact**: Medium
**Estimated Lines Saved**: ~300 lines

## New Common Module Structure

```
common/
├── __init__.py              # Existing
├── config_loader.py         # Existing
├── logger.py                # Existing
├── type_mapping.py          # Existing
├── utils.py                 # Existing (enhance)
├── schema_utils.py          # NEW - Schema conversion utilities
├── input_handlers.py        # NEW - Input processing utilities
├── output_handlers.py       # NEW - Output processing utilities
├── logging_utils.py         # NEW - Logging utilities
├── dry_run.py              # NEW - Dry run utilities
└── debug_utils.py          # NEW - Debug utilities
```

## Implementation Strategy

1. **Create new common modules** with extracted functions
2. **Add API parameter** to functions that need API-specific behavior
3. **Update imports** in all three API implementations
4. **Remove duplicate functions** from API implementations
5. **Test each API** to ensure no regression
6. **Update documentation** to reflect new structure

## Testing Strategy

- Run existing test suite after each phase
- Test each API individually (FalAi, HuggingFace, Replicate)
- Verify dry_run mode works correctly
- Verify debug mode works correctly
- Test with various model schemas

## Success Criteria

- [ ] All duplicate functions moved to common modules
- [ ] All three APIs use common functions
- [ ] No regression in functionality
- [ ] All tests pass
- [ ] Code is more maintainable
- [ ] Documentation updated

## Estimated Total Impact

- **Lines of Code Reduced**: ~1600+ lines
- **Files Modified**: 6 files (2 per API)
- **New Files Created**: 5 files (in common/)
- **Maintenance Improvement**: High
- **Consistency Improvement**: High
