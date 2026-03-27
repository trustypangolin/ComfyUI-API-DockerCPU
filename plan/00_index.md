# Refactoring Plans Index

This directory contains detailed plans for extracting common functions from the three API implementations (FalAi, HuggingFace, Replicate) into shared utility modules.

## Quick Reference

### Overview
- [00_overview.md](00_overview.md) - Overall refactoring plan and strategy

### Phase 1: Schema Utilities (Quick Wins)
- [01_is_type.md](01_is_type.md) - Extract `is_type()` function
- [02_get_input_type_from_config.md](02_get_input_type_from_config.md) - Extract `get_input_type_from_config()` function
- [03_parameter_ordering_functions.md](03_parameter_ordering_functions.md) - Extract parameter ordering functions
- [04_get_output_name_with_alias.md](04_get_output_name_with_alias.md) - Extract `get_output_name_with_alias()` function
- [05_get_model_config_override.md](05_get_model_config_override.md) - Extract `get_model_config_override()` function
- [06_convert_to_comfyui_input_type.md](06_convert_to_comfyui_input_type.md) - Extract `convert_to_comfyui_input_type()` function

### Phase 2: Input/Output Handlers
- [07_handle_image_output.md](07_handle_image_output.md) - Extract `handle_image_output()` function
- [08_handle_audio_output.md](08_handle_audio_output.md) - Extract `handle_audio_output()` function
- [09_handle_array_inputs.md](09_handle_array_inputs.md) - Extract `handle_array_inputs()` function
- [10_remove_falsey_optional_inputs.md](10_remove_falsey_optional_inputs.md) - Extract `remove_falsey_optional_inputs()` function
- [11_convert_input_images_to_base64.md](11_convert_input_images_to_base64.md) - Extract `convert_input_images_to_base64()` function

### Phase 3: Utility Functions
- [12_image_to_base64.md](12_image_to_base64.md) - Enhance `image_to_base64()` function
- [13_audio_to_base64.md](13_audio_to_base64.md) - Enhance `audio_to_base64()` function
- [14_base64_to_tensor.md](14_base64_to_tensor.md) - Enhance `base64_to_tensor()` function

### Phase 4: Logging & Debug
- [15_log_input.md](15_log_input.md) - Extract `_log_input()` function
- [16_dry_run_output.md](16_dry_run_output.md) - Extract `_dry_run_output()` function
- [17_debug_schema_conversion.md](17_debug_schema_conversion.md) - Extract `debug_schema_conversion()` function
- [18_get_standard_parameters.md](18_get_standard_parameters.md) - Extract `get_standard_parameters()` function

### Phase 5: Additional Functions
- [19_process_output.md](19_process_output.md) - Extract `_process_output()` function
- [20_extract_max_items_from_description.md](20_extract_max_items_from_description.md) - Extract `extract_max_items_from_description()` function
- [21_get_input_name_with_alias.md](21_get_input_name_with_alias.md) - Extract `get_input_name_with_alias()` function
- [22_get_schema_from_json.md](22_get_schema_from_json.md) - Extract `get_schema_from_json()` function
- [23_get_array_config.md](23_get_array_config.md) - Extract `get_array_config()` function
- [24_get_max_images_and_array_input_mapping.md](24_get_max_images_and_array_input_mapping.md) - Extract `get_max_images()` and `get_array_input_mapping()` functions
- [25_combine_split_image_inputs.md](25_combine_split_image_inputs.md) - Extract `combine_split_image_inputs()` function
- [26_base64_encode.md](26_base64_encode.md) - Extract `base64_encode()` function
- [27_format_value_for_log.md](27_format_value_for_log.md) - Document `format_value_for_log()` function
- [28_convert_to_json_serializable.md](28_convert_to_json_serializable.md) - Document `convert_to_json_serializable()` function
- [29_pil_image_to_tensor.md](29_pil_image_to_tensor.md) - Document `pil_image_to_tensor()` function
- [30_tensor_to_pil_image.md](30_tensor_to_pil_image.md) - Document `tensor_to_pil_image()` function
- [31_base64_audio_to_tensor.md](31_base64_audio_to_tensor.md) - Document `base64_audio_to_tensor()` function
- [32_resolve_schema.md](32_resolve_schema.md) - Extract `resolve_schema()` function
- [33_get_default_example_input.md](33_get_default_example_input.md) - Extract `get_default_example_input()` function
- [34_inputs_that_need_arrays.md](34_inputs_that_need_arrays.md) - Extract `inputs_that_need_arrays()` function
- [35_name_and_version.md](35_name_and_version.md) - Keep `name_and_version()` separate (API-specific)
- [36_create_nodes.md](36_create_nodes.md) - Keep `create_nodes()` separate (API-specific)

### Already Extracted Functions (Document Only)
- [37_get_comfyui_output_type.md](37_get_comfyui_output_type.md) - Document `get_comfyui_output_type()` function
- [38_validate_output_type.md](38_validate_output_type.md) - Document `validate_output_type()` function
- [39_normalize_type_name.md](39_normalize_type_name.md) - Document `normalize_type_name()` function
- [40_get_output_type_from_config.md](40_get_output_type_from_config.md) - Document `get_output_type_from_config()` function
- [41_infer_type_from_example.md](41_infer_type_from_example.md) - Document `infer_type_from_example()` function
- [42_is_media_type.md](42_is_media_type.md) - Document `is_media_type()` function
- [43_get_standardized_output_name.md](43_get_standardized_output_name.md) - Document `get_standardized_output_name()` function
- [44_get_input_alias.md](44_get_input_alias.md) - Document `get_input_alias()` function
- [45_get_input_mapping.md](45_get_input_mapping.md) - Document `get_input_mapping()` function
- [46_get_model_config.md](46_get_model_config.md) - Document `get_model_config()` function
- [47_get_config.md](47_get_config.md) - Document `get_config()` function
- [48_config_loader_class.md](48_config_loader_class.md) - Document `ConfigLoader` class
- [49_logger.md](49_logger.md) - Document `logger` module

### Configuration Files (Document Only)
- [50_init_files.md](50_init_files.md) - Document `__init__.py` files
- [51_pyproject.toml.md](51_pyproject.toml.md) - Document `pyproject.toml` file
- [52_requirements.txt.md](52_requirements.txt.md) - Document `requirements.txt` file
- [53_readme.md](53_readme.md) - Document `README.md` file
- [54_gitignore.md](54_gitignore.md) - Document `.gitignore` file
- [55_load_env.sh.md](55_load_env.sh.md) - Document `load_env.sh` file
- [56_yaml_configs.md](56_yaml_configs.md) - Document YAML configuration files
- [57_import_schemas.md](57_import_schemas.md) - Document `import_schemas.py` file
- [58_tests.md](58_tests.md) - Document `tests` directory
- [59_schemas.md](59_schemas.md) - Document `schemas` directory
- [60_example_workflows.md](60_example_workflows.md) - Document `example_workflows` directory
- [61_cpu_requirements.md](61_cpu_requirements.md) - Document `cpu-requirements.txt` file
- [62_tests_init.md](62_tests_init.md) - Document `tests/__init__.py` file
- [63_conftest.md](63_conftest.md) - Document `conftest.py` file
- [64_test_api.md](64_test_api.md) - Document `test_api.py` file
- [65_test_schemas.md](65_test_schemas.md) - Document `test_schemas.py` file
- [66_schemas_readme.md](66_schemas_readme.md) - Document `schemas/README.md` file
- [67_api_init.md](67_api_init.md) - Document `API/__init__.py` file
- [68_falai_init.md](68_falai_init.md) - Document `API/FalAi/__init__.py` file
- [69_huggingface_init.md](69_huggingface_init.md) - Document `API/HuggingFace/__init__.py` file
- [70_replicate_init.md](70_replicate_init.md) - Document `API/Replicate/__init__.py` file
- [71_common_init.md](71_common_init.md) - Document `common/__init__.py` file
- [72_config_loader.md](72_config_loader.md) - Document `common/config_loader.py` file
- [73_logger.md](73_logger.md) - Document `common/logger.py` file
- [74_type_mapping.md](74_type_mapping.md) - Document `common/type_mapping.py` file
- [75_utils.md](75_utils.md) - Document `common/utils.py` file
- [76_falai_node.md](76_falai_node.md) - Document `API/FalAi/node.py` file
- [77_falai_schema_to_node.md](77_falai_schema_to_node.md) - Document `API/FalAi/schema_to_node.py` file
- [78_huggingface_node.md](78_huggingface_node.md) - Document `API/HuggingFace/node.py` file
- [79_huggingface_schema_to_node.md](79_huggingface_schema_to_node.md) - Document `API/HuggingFace/schema_to_node.py` file
- [80_replicate_node.md](80_replicate_node.md) - Document `API/Replicate/node.py` file
- [81_replicate_schema_to_node.md](81_replicate_schema_to_node.md) - Document `API/Replicate/schema_to_node.py` file
- [82_root_init.md](82_root_init.md) - Document `__init__.py` file (root)

### Summary
- [83_summary.md](83_summary.md) - Summary of all refactoring plans

## How to Use These Plans

1. **Start with Phase 1** - These are quick wins with low risk
2. **Follow the implementation steps** in each plan
3. **Test thoroughly** after each function is extracted
4. **Update imports** in all API files
5. **Remove duplicate functions** from API files
6. **Run full test suite** to ensure no regression

## Estimated Total Impact

- **Lines of Code Reduced**: ~1600+ lines
- **Files Modified**: 6 files (2 per API)
- **New Files Created**: 5 files (in common/)
- **Maintenance Improvement**: High
- **Consistency Improvement**: High
