# ComfyUI-API-DockerCPU

Unified ComfyUI custom nodes for external API integration (Replicate, Fal.ai, HuggingFace).

## Overview

This package combines multiple external API integrations into a single ComfyUI extension:

- **Replicate API** (`🎨 DockerCPU API/🎨 Replicate`) - Run models from Replicate
- **Fal.ai API** (`🎨 DockerCPU API/🎨 FalAi`) - Run models from Fal.ai
- **HuggingFace Hub** (`🎨 DockerCPU API/🤗 HuggingFace`) - Browse and select models from HuggingFace

## Docker Deployment

This custom node is designed to be used in conjunction with **[ComfyUI_API-DockerContainer](https://github.com/trustypangolin/ComfyUI_API-DockerContainer)** — a Docker build that runs ComfyUI on systems without a dedicated GPU, such as virtual machines or CPU-only servers.

All inference is offloaded to cloud APIs (Replicate, Fal.ai, HuggingFace), so no local GPU is required.

### Key Features

- **DockerCPU Design**: No local model downloads. All inference runs externally via APIs.
- **Debug/Dry-Run Mode**: Test workflows without API costs by enabling debug mode on any node
- **Unified Structure**: Single extension for all API integrations
- **Comprehensive Tests**: Test outside ComfyUI to validate inputs, outputs, and parameters

## Installation

### Prerequisites

- ComfyUI installed
- Python 3.10+

### Steps

1. Clone or copy this folder to your ComfyUI custom_nodes directory:
   ```
   ComfyUI/custom_nodes/ComfyUI-API-DockerCPU/
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set required environment variables:
   ```bash
   export REPLICATE_API_TOKEN="your_token_here"      # Required for Replicate
   export FAL_KEY="your_fal_key_here"                # Required for Fal.ai
   export HF_TOKEN="your_hf_token_here"              # Optional (for private repos)
   ```

## Usage

### Schema-Based Nodes (Replicate & Fal.ai)

Nodes are automatically generated from API schemas. Each model has its own node with:
- Dynamic INPUT_TYPES based on the model's parameters
- IMAGE, AUDIO, and STRING inputs
- IMAGE, AUDIO, and STRING outputs
- JSON payload output for debugging

#### Replicate Nodes

Example: `Replicate black-forest-labs/flux-2-klein-9b`

Available in category: `🎨 DockerCPU API/Replicate`

#### Fal.ai Nodes

Example: `Fal AI fal-ai/seedvr/upscale/image`

Available in category: `🎨 DockerCPU API/FalAi`

### HuggingFace Nodes

#### HF Model Selector
Browse and select safetensor models from configured HuggingFace repositories.

#### HF Lora Combiner
Combine multiple Lora URLs into an array for use with other nodes.

#### HF Lora URL Builder
Build HuggingFace URLs from repository ID and filename.

Available in category: `🤗 HuggingFace`

## Debug/Dry-Run Mode

All schema-based nodes support debug mode:

1. Add a `debug` boolean input to your workflow
2. Set it to `True`
3. The node will:
   - Skip the actual API call
   - Return the first input image as a mock output
   - Output the JSON payload that would have been sent

This is useful for:
- Testing workflows without API costs
- Debugging parameter configurations
- Validating workflow connections

## Schema Management

### Updating Schemas

Fetch latest schemas from APIs:

```bash
# Update all schemas
python import_schemas.py --update

# Update specific API
python import_schemas.py --api replicate
python import_schemas.py --api falai
```

### Configuration

The node generation/config stack is YAML-based.

- `supported_models.yaml`: Provider/model/repo allowlist and per-model overrides
- `global_inputs.yaml`: Global media input pattern mapping
- `global_parameters.yaml`: Global non-media parameter mapping and ordering
- `global_outputs.yaml`: Global output inference/exposure rules

Example (`supported_models.yaml`):

```yaml
replicate:
  models:
    black-forest-labs/flux-2-klein-9b:
      display_name: "FLUX.2 [klein] 9B"

falai:
  models:
    fal-ai/seedvr/upscale/image:
      display_name: "SeedVR Upscale Image"

huggingface:
  repos:
    renderartist/Technically-Color-Z-Image-Turbo:
      display_name: "Color Z Image Turbo"
```

## Testing

Run tests outside of ComfyUI:

```bash
# Run all tests
python -m pytest tests/

# Or run the schema test script directly
python tests/test_schemas.py
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REPLICATE_API_TOKEN` | Replicate API token | Yes |
| `FAL_KEY` | Fal.ai API key | Yes |
| `HF_TOKEN` | HuggingFace token | No (required for private repos) |
| `DEBUG_API_TRUSTYPANGOLIN` | Enable debug output | No |

### Utility Nodes

Available in category: `🎨 DockerCPU API/Utilities`

- **Load Image With Metadata** - Loads an image from the input folder and extracts embedded prompt, workflow, and EXIF metadata
  - Outputs: `IMAGE`, `MASK`, `prompt` (JSON), `Metadata RAW`, `BASE_FILENAME`, `BASE_DIR`
- **Load ZIP Archive** - Load PNG images from a ZIP file URL or path
- **Load Replicate Prediction** - Load output from a Replicate prediction by ID
- **Save AMD Video** - Save video with AMD GPU audio fix patch
- **Save Text With Filename** - Save text content to a file named after the source image
  - Inputs: `text`, `base_dir`, `base_filename`, `replace_extension` (BOOLEAN), `extension` (STRING)

## Supported Models

### Replicate Models

| Model ID | Display Name | Category | Description |
|----------|-------------|----------|-------------|
| `black-forest-labs/flux-2-klein-9b` | FLUX.2 [klein] 9B | image-generation | Fast, high-quality text-to-image generation |
| `black-forest-labs/flux-2-klein-9b-base-lora` | FLUX.2 [klein] 9B Base LoRA | image-generation | Fast fine-tuned LoRA inference |
| `black-forest-labs/flux-2-max` | FLUX.2 [max] | image-generation | Highest fidelity image model |
| `black-forest-labs/flux-2-pro` | FLUX.2 [pro] | image-generation | Professional image generation |
| `google/nano-banana` | Google Nano Banana | image-generation | Fast, high-quality text-to-image |
| `google/nano-banana-pro` | Google Nano Banana Pro | image-generation | Pro version with more images |
| `google/nano-banana-2` | Google Nano Banana 2 | image-generation | Extended version |
| `openai/gpt-5` | OpenAI GPT-5 | image-understanding | Image-to-text generation for captions |
| `lucataco/qwen3-vl-8b-instruct` | Qwen3-VL-8B Instruct | image-understanding | Multimodal vision-language model |
| `mattsays/sam3-image` | SAM3 Image | image-segmentation | Prompt-based segmentation |
| `papina/seedvr2` | SeedVR 2 | image-upscaling | Realistic vision enhancement |
| `philz1337x/crystal-upscaler` | Crystal Upscaler | image-upscaling | High-quality image upscaler |
| `topazlabs/image-upscale` | TopazLabs Image Upscale | image-upscaling | Professional image upscaling |
| `sczhou/codeformer` | CodeFormer | face-restoration | Face restoration and enhancement |
| `zsxkib/seedvr2` | SeedVR 2 Video | video-upscaling | Video upscaling |
| `zsxkib/realistic-voice-cloning` | Realistic Voice Cloning | audio-processing | AI song covers with RVC voice models |
| `prunaai/z-image-turbo-lora` | Z-Image Turbo LoRA | image-generation | Fast generation with LoRA support |
| `tencentarc/gfpgan` | GFPGAN | face-restoration | Face restoration |

### Fal.ai Models

| Model ID | Display Name | Category | Description |
|----------|-------------|----------|-------------|
| `fal-ai/flux-2/klein/9b/edit` | FLUX.2 [klein] 9B Edit | image-editing | Image editing with FLUX.2 Klein |
| `fal-ai/seedvr/upscale/image` | SeedVR Upscale Image | image-upscaling | Image upscaling with SeedVR |

### HuggingFace Repos

| Repo ID | Display Name | Category | Description |
|---------|-------------|----------|-------------|
| `renderartist/Technically-Color-Z-Image-Turbo` | Color Z Image Turbo | image-processing | Colorization with style transfer |
| `starsfriday/FLUX.2-klein-AC-Style-LORA` | AC Style LORA | image-generation | Anime/Comic style LoRA for FLUX |
| `Papina/Lora-Characters` | LORA Characters | image-generation | Character style LoRA |

## Directory Structure

```
ComfyUI-API-DockerCPU/
├── __init__.py                      # Main entry point
├── pyproject.toml                   # ComfyUI Registry config
├── requirements.txt                 # Dependencies
├── README.md                        # This file
│
├── API/                             # API-specific implementations
│   ├── Replicate/
│   │   ├── node.py                  # Dynamic node creation
│   │   └── schema_to_node.py        # Schema parsing
│   ├── FalAi/
│   │   ├── node.py                  # Dynamic node creation
│   │   └── schema_to_node.py        # Schema parsing
│   └── HuggingFace/
│       └── node.py                  # Model selector & utilities
│
├── common/                          # Shared utilities
│   ├── utils.py                     # Image/audio conversion
│   ├── logger.py                    # Logging utilities
│   ├── zip_utils.py                 # ZIP archive loading
│   ├── amd_tools.py                 # AMD GPU patch
│   ├── image_utils.py               # Load Image With Metadata
│   └── text_saver.py                # Save Text With Filename
│
├── schemas/                         # API schema definitions
│   ├── Replicate/*.json
│   ├── FalAi/*.json
│   └── HuggingFace/*.json
│
└── tests/                           # Test suite
    └── test_schemas.py              # Schema validation tests
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## Support

- GitHub Issues: https://github.com/trustypangolin/ComfyUI-API-DockerCPU/issues
- Wiki: https://github.com/trustypangolin/ComfyUI-API-DockerCPU/wiki
