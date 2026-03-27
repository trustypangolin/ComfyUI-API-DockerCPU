# Schemas Directory

This directory contains API schemas for ComfyUI-API-DockerCPU.

## Structure

```
schemas/
├── README.md           # This file
├── Replicate/          # Replicate API schemas (OpenAPI 3.0 JSON)
│   ├── black-forest-labs_flux-2-klein-9b.json
│   └── ...
├── FalAi/              # Fal.ai API schemas (OpenAPI 3.0 JSON)
│   ├── fal-ai_flux-2_klein_9b_edit.json
│   └── ...
└── HuggingFace/        # HuggingFace model metadata (JSON)
    ├── stabilityai_stable-diffusion-3-medium.json
    └── ...
```

## Usage

Schemas are automatically loaded by the respective API modules:
- Replicate nodes load from `schemas/Replicate/`
- Fal.ai nodes load from `schemas/FalAi/`
- HuggingFace nodes load from `schemas/HuggingFace/`

## Schema Formats

### Replicate (OpenAPI 3.0)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Model Name",
    "description": "Model description",
    "version": "1.0.0"
  },
  "components": {
    "schemas": {
      "Input": { ... },
      "Output": { ... }
    }
  }
}
```

### FalAi (OpenAPI 3.0)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "fal-ai/model-name",
    "description": "Model description"
  },
  "components": {
    "schemas": {
      "Input": { ... },
      "Output": { ... }
    }
  }
}
```

### HuggingFace (Model Metadata)

```json
{
  "id": "stabilityai/stable-diffusion-3-medium",
  "name": "stable-diffusion-3-medium",
  "sha": "abc123...",
  "createdAt": "2024-01-15T00:00:00.000Z",
  "private": false,
  "gated": false,
  "downloads": 10000,
  "tags": ["text-to-image", "stable-diffusion"],
  "pipeline_tag": "text-to-image",
  "models": [
    {
      "id": "model",
      "filename": "sd3_medium.safetensors",
      "size": 5000000000,
      "sha256": "def456...",
      "path": "sd3_medium.safetensors"
    }
  ]
}
```

**HuggingFace Fields:**
- `id`: Full repository ID (filename uses `_` instead of `/`)
- `name`: Short model name
- `sha`: Repository SHA
- `createdAt`: Creation timestamp (ISO 8601)
- `private`: Whether the model is private
- `gated`: Whether the model requires approval
- `downloads`: Number of downloads
- `tags`: List of model tags
- `pipeline_tag`: ML pipeline type
- `models`: List of safetensor file metadata

## Fetching Schemas

Run the import script to fetch schemas from APIs:

```bash
# Fetch all schemas
python import_schemas.py

# Fetch specific API
python import_schemas.py --api replicate
python import_schemas.py --api falai
python import_schemas.py --api huggingface

# Update all existing schemas
python import_schemas.py --update
```

## Supported Models

Edit `supported_models.json` in the root directory to add/remove models:
- Replicate models: `replicate.models` section
- FalAi models: `falai.models` section
- HuggingFace repos: `huggingface.repos` section

## Manual Addition

You can also manually add JSON schema files to the respective folders.
