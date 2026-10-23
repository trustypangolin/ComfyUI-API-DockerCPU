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
| `LOCAL_LLM_API_KEY` | API key for the Local LLM node when its `api_key` widget is empty. `LocalLLM` is also accepted | No (LM Studio needs none) |
| `LOCAL_LLM_ENDPOINT` | Endpoint for the Local LLM node when its `endpoint_url` widget is empty (default `http://localhost:1234`) | No |
| `DEBUG_API_TRUSTYPANGOLIN` | Enable debug output | No |

Prefer the environment variables over typing a key into the Local LLM widget: widget values are saved in the workflow JSON and embedded in every output image's metadata. If a Local LLM variable isn't set in the environment, the node reads it from `.env` at this repo's root (gitignored). Only the Local LLM keys are read from that file.

### Utility Nodes

Available in category: `🎨 DockerCPU API/Utilities`

- **Load Image With Metadata** - Loads an image from the input folder and extracts embedded prompt, workflow, and EXIF metadata
  - Outputs: `IMAGE`, `MASK`, `prompt` (JSON), `Metadata RAW`, `BASE_FILENAME`, `BASE_DIR`, `height`, `width`, `megapixels`, `REL_DIR` (folder relative to input, e.g. `originals/1990`), `STEM` (name without extension), `SHA256` (file hash), `ORIGINAL`, `ORIGINAL_SHA256` (see Provenance below)
  - The Crop variant has the same optional `library_root` and the same two trailing outputs
- **Load Images From Folder With Metadata** - Loads every image in an input subfolder in natural order (`img2` before `img10`), as lists at native size
  - Inputs: `folder`, `pattern` (case-insensitive glob), `recursive`, `strip_prefix` (default `originals/`), `start_index`, `limit` (0 = all)
  - Outputs (lists): `image`, `mask`, `BASE_FILENAME`, `STEM`, `REL_DIR`, `MIRROR_DIR` (`REL_DIR` minus `strip_prefix`), `SHA256`, `width`, `height`, `ORIGINAL`, `ORIGINAL_SHA256`
  - **Provenance** (all three loaders): `ORIGINAL` is the PrimaryLibrary file the image derives from (`"1992 Feb/img0018.jpg"`), `ORIGINAL_SHA256` that library file's hash; both `""` when unknown. Resolved from the input PNG's `restore` chunk (carried `original` + `original_sha256`, checked against the library; or `source`, followed recursively up to 8 hops), else from `input/originals/<album>/<file>` when the library twin has the same SHA-256. Optional `library_root` widget, else env `PRIMARY_LIBRARY`, else `C:/Users/luton/OneDrive/Pictures/PrimaryLibrary`; when that folder is missing (Docker) only carried values are used, unchecked. Only the one candidate library file is hashed
- **Load Prompt From File** - Pick a `.txt` file under `input/prompts/` (subfolders included, alphabetical) from a dropdown; outputs its `text`
  - `reload`: `if file changed` (default) re-reads after you edit the file; `if value changed` only when another file is picked. Press R in ComfyUI to refresh the list
- **Save Image With Filename** - Writes `output/<stage>/<mirror_dir>/<stem><suffix>.png` with no counter (`_00`, `_01`, ... for batches > 1)
  - `if_exists`: `error` (default) / `overwrite` / `skip`. Embeds prompt and workflow like Save Image
  - Always writes the PNG text key `restore`: `extra_metadata` (a JSON object, or `{}`) plus `"schema": 1`, `"original"`, `"original_sha256"` from the optional `original` / `original_sha256` inputs (wire the loader's `ORIGINAL` / `ORIGINAL_SHA256`; empty or unconnected → `null`, and they override the same keys in `extra_metadata`)
  - Refuses paths outside the output folder and anything under the input folder
- **Load ZIP Archive** - Load PNG images from a ZIP file URL or path
- **Load Replicate Prediction** - Load output from a Replicate prediction by ID
- **Save AMD Video** - Save video with AMD GPU audio fix patch
- **Save Text With Filename** - Save text content to a file named after the source image
  - Inputs: `text`, `base_dir`, `base_filename`, `replace_extension` (BOOLEAN), `extension` (STRING)
  - `output_mode`: `base_dir` (write into `base_dir`) or `output_stage` (same `stage` / `mirror_dir` / `stem` / `suffix` path rule as Save Image With Filename)
  - Refuses to write under the input folder unless `allow_input_dir` is on; `if_exists` defaults to `overwrite`

### Face Nodes

Available in category: `🎨 DockerCPU API/Face`. All run on CPU; a GPU is used when available.

- **Face Analyze (InsightFace ONNX)** - SCRFD detection + 512-d ArcFace embeddings via `onnxruntime` (no `insightface` package). Models from `models/insightface` (e.g. `buffalo_l/det_10g.onnx`, `buffalo_l/w600k_r50.onnx`); add an `insightface:` key to `extra_model_paths.yaml` if your models live elsewhere
  - `sort`: `left_to_right` (default, box centre-x) or `score`; applied to every output, so face *k* is the same face everywhere
  - Outputs: `bboxes` (native `BOUNDING_BOX`), `face_analysis`, `face_count`, `scores`, `faces_json` (`{frame, index, x, y, width, height, score}`, index 1-based)
- **Draw Numbered BBoxes** - Draws boxes with legible number labels (PIL only); accepts the same `BOUNDING_BOX` shapes as native Draw BBoxes
  - Inputs: `image`, `bboxes`, `sort` (`as_given` / `left_to_right`), `start_index`, `line_width` (0 = auto), `font_scale` (label height as a fraction of the short edge, 0 = auto), `color`, `show_score`
  - Outputs: `image`, `bboxes` (in drawn order), `labels_json`
- **Face Similarity (ArcFace)** - Cosine similarity of one face against a `reference_analysis` and/or a `reference_folder` of images and `.npy` embeddings (subfolder names become labels)
  - Outputs: `best_score`, `best_match`, `ranking` (JSON)
- **Face Identify (ArcFace)** - Every face in one image vs a reference folder (`<folder>/<Label>/*.png|jpg|npy`, relative to the input folder or absolute). Per-label scores combine by `max` or `mean_top3`; a label is assigned when the best score reaches `threshold` and beats the best other label by `margin`, else `unknown_label`
  - List outputs, one per face: `face_crop` (square, `crop_pad` × bbox, native resolution), `label`, `score`, `runner_up`, `runner_up_score`, `suffix` (`_p01`…), `subfolder`, `crop_box_json`, `restore_json` (wire into Save Image With Filename `extra_metadata`); plus `summary_json`; then `mirror_dir`, `stem` (the optional inputs repeated per face) and `save_dir` (`<label>/<mirror_dir>`), so batch runs pair each face with its own image when saving. Optional `suffix_extra` is appended to each suffix (`_p01_head`)
- **Face Cluster (ArcFace)** - Batch node: groups all faces from a folder (average-linkage, cosine distance ≤ `distance_threshold`) into `cluster_01` (largest) … and `singles`, to bootstrap reference folders
- **Collect Labelled Faces** - Reads a review done by moving crops between `<review_root>/<Label>/<folder>/` folders into a CSV (`changed` = moved from the original label). Optionally copies confirmed crops into `<references_root>/<Label>/` under the input folder (needs `allow_input_dir`; never `originals/`; honours `exclude_list` and `skip_labels`)
- Face crops saved with `restore_json` carry their face keypoints, so they work as references without re-detection
- **Load Face Detection Model (MediaPipe, device)** - Native MediaPipe face landmarker loaded on `cpu` or the `default` device; works with the native MediaPipe detect / mask nodes

Install `onnxruntime` (CPU) or `onnxruntime-gpu` for the InsightFace nodes; `cpu-requirements.txt` includes the CPU build.

### Touch/Pencil Usability

On touch devices (e.g. iPad, detected via `navigator.maxTouchPoints`), this extension enlarges LiteGraph's context menu and combo-widget value-list rows (`.litemenu-entry`), which ship at a 12px font with 2px padding - too small to reliably tap with a finger or Apple Pencil. It also turns an Apple Pencil tap on a menu/list entry into a click, because Safari often doesn't send one for pen taps (e.g. with Scribble enabled), so the pencil selects entries the way a finger does. While the pencil is down on the graph canvas, it also hides tiny pencil movements (within LiteGraph's 6px click drift) from the canvas, so a pencil tap counts as a click rather than a drag. This makes widget arrows and combo dropdowns respond to the pencil.

Palm rejection: **Settings → DockerCPU → Pencil → Ignore finger touches** blocks all finger input, so you can rest your hand on the screen while using the pencil. After the first pencil tap, a floating **✏️** toggle appears in the bottom-right corner to switch this on and off. A finger can always tap the toggle, so you can't lock yourself out. Hide the toggle with **Show pencil toggle when a pencil is used**. Apple Pencil double-tap and squeeze aren't supported: Safari doesn't make them available to web pages. Desktop mouse/trackpad usage is unaffected. See [web/touch_usability.js](web/touch_usability.js).

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
│   ├── provenance.py                # ORIGINAL / ORIGINAL_SHA256 resolution
│   ├── prompt_loader.py             # Load Prompt From File
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
