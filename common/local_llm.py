import base64
from io import BytesIO
from urllib.parse import urljoin

import numpy as np
import requests
import torch
from PIL import Image

try:
    from aiohttp import web
    from server import PromptServer
    ROUTES_AVAILABLE = True
except Exception:
    web = None
    PromptServer = None
    ROUTES_AVAILABLE = False


def normalize_endpoint_url(endpoint_url):
    endpoint_url = (endpoint_url or "http://localhost:1234").strip().rstrip("/")
    if not endpoint_url:
        endpoint_url = "http://localhost:1234"
    return endpoint_url


def build_headers(api_key):
    headers = {"Content-Type": "application/json"}
    api_key = (api_key or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def raise_for_status_with_body(response):
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        body = response.text.strip()
        if body:
            raise requests.HTTPError(f"{e}: {body}", response=response) from e
        raise


def openai_url(endpoint_url, path):
    endpoint_url = normalize_endpoint_url(endpoint_url)
    path = path.lstrip("/")
    if endpoint_url.endswith("/v1"):
        return urljoin(f"{endpoint_url}/", path)
    return urljoin(f"{endpoint_url}/", f"v1/{path}")


def lmstudio_url(endpoint_url, path):
    endpoint_url = normalize_endpoint_url(endpoint_url)
    path = path.lstrip("/")
    if endpoint_url.endswith("/v1"):
        endpoint_url = endpoint_url[:-3]
    return urljoin(f"{endpoint_url}/", f"api/v1/{path}")


def fetch_openai_models(endpoint_url, api_key="", timeout=10):
    response = requests.get(
        openai_url(endpoint_url, "models"),
        headers=build_headers(api_key),
        timeout=timeout,
    )
    raise_for_status_with_body(response)
    payload = response.json()
    models = []
    for item in payload.get("data", []):
        if isinstance(item, dict) and item.get("id"):
            models.append(str(item["id"]))
        elif isinstance(item, str):
            models.append(item)
    return models


def fetch_lmstudio_models(endpoint_url, api_key="", timeout=10):
    response = requests.get(
        lmstudio_url(endpoint_url, "models"),
        headers=build_headers(api_key),
        timeout=timeout,
    )
    raise_for_status_with_body(response)
    payload = response.json()
    loaded = []
    unloaded = []
    for item in payload.get("models", []):
        if item.get("type") != "llm":
            continue
        instances = item.get("loaded_instances") or []
        for instance in instances:
            instance_id = instance.get("id")
            if instance_id:
                loaded.append(str(instance_id))
        key = item.get("key")
        if key and str(key) not in loaded:
            unloaded.append(str(key))
    return loaded + [model for model in unloaded if model not in loaded]


def fetch_models(endpoint_url, api_type, api_key="", timeout=10):
    if api_type == "lmstudio_native":
        return fetch_lmstudio_models(endpoint_url, api_key, timeout)
    return fetch_openai_models(endpoint_url, api_key, timeout)


def image_to_data_uri(image):
    if isinstance(image, torch.Tensor):
        if image.dim() == 4:
            image = image[0]
        if image.dim() != 3:
            raise ValueError(f"Expected 3D or 4D image tensor, got {image.dim()}D")
        image = image.detach().cpu().numpy()
        if image.max() <= 1.0:
            image = (image * 255).clip(0, 255).astype(np.uint8)
        else:
            image = image.clip(0, 255).astype(np.uint8)
        if image.shape[2] == 1:
            image = image[:, :, 0]
        pil_image = Image.fromarray(image)
    else:
        pil_image = image

    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")

    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def unload_lmstudio_models(endpoint_url, api_key="", timeout=10):
    response = requests.get(
        lmstudio_url(endpoint_url, "models"),
        headers=build_headers(api_key),
        timeout=timeout,
    )
    raise_for_status_with_body(response)
    payload = response.json()
    unloaded = []
    for model in payload.get("models", []):
        for instance in model.get("loaded_instances", []):
            instance_id = instance.get("id")
            if not instance_id:
                continue
            unload_response = requests.post(
                lmstudio_url(endpoint_url, "models/unload"),
                headers=build_headers(api_key),
                json={"instance_id": instance_id},
                timeout=timeout,
            )
            raise_for_status_with_body(unload_response)
            unloaded.append(instance_id)
    return unloaded


def get_loaded_lmstudio_instance(endpoint_url, model, api_key="", timeout=10):
    response = requests.get(
        lmstudio_url(endpoint_url, "models"),
        headers=build_headers(api_key),
        timeout=timeout,
    )
    raise_for_status_with_body(response)
    payload = response.json()
    for item in payload.get("models", []):
        key = str(item.get("key") or "")
        if key != model:
            continue
        for instance in item.get("loaded_instances", []):
            instance_id = instance.get("id")
            if instance_id:
                return str(instance_id)
    return None


def load_lmstudio_model(endpoint_url, model, api_key="", timeout=10, skip_loaded_check=False):
    if not skip_loaded_check:
        instance_id = get_loaded_lmstudio_instance(endpoint_url, model, api_key, timeout)
        if instance_id:
            return instance_id
    response = requests.post(
        lmstudio_url(endpoint_url, "models/load"),
        headers=build_headers(api_key),
        json={"model": model},
        timeout=timeout,
    )
    raise_for_status_with_body(response)
    payload = response.json()
    return payload.get("instance_id") or model


def extract_text_parts(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
            elif item is not None:
                parts.append(str(item))
        return "\n".join(parts)
    return ""


def extract_response_text(payload):
    choices = payload.get("choices") or []
    if choices:
        first = choices[0]
        message = first.get("message") or {}
        content = message.get("content")
        text = extract_text_parts(content)
        if text:
            return text
        if first.get("text"):
            return str(first["text"])
    if payload.get("output_text"):
        return str(payload["output_text"])
    output = payload.get("output") or []
    if output:
        parts = []
        for item in output:
            if isinstance(item, dict) and item.get("type") == "message" and item.get("content"):
                parts.append(str(item["content"]))
        if parts:
            return "\n".join(parts)
    return str(payload)


def build_openai_payload(selected_model, prompt, system_prompt, temperature, max_tokens, image=None):
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    if image is not None:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_to_data_uri(image)}},
            ],
        })
    else:
        messages.append({"role": "user", "content": prompt})
    return {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def build_lmstudio_payload(selected_model, prompt, system_prompt, temperature, max_tokens, image=None):
    if image is not None:
        input_value = [
            {"type": "text", "content": prompt},
            {"type": "image", "data_url": image_to_data_uri(image)},
        ]
    else:
        input_value = prompt
    payload = {
        "model": selected_model,
        "input": input_value,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "store": False,
    }
    if system_prompt.strip():
        payload["system_prompt"] = system_prompt
    return payload


if ROUTES_AVAILABLE:
    @PromptServer.instance.routes.get("/dockercpu/local_llm/models")
    async def get_local_llm_models(request):
        endpoint_url = request.query.get("endpoint_url", "http://localhost:1234")
        api_key = request.query.get("api_key", "")
        timeout = int(request.query.get("timeout", "10"))
        api_type = request.query.get("api_type", "openai_compatible")
        try:
            models = fetch_models(endpoint_url, api_type, api_key, timeout)
            return web.json_response({"models": models})
        except Exception as e:
            return web.json_response({"error": str(e), "models": []}, status=500)


class LocalLLM:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "endpoint_url": ("STRING", {"default": "http://localhost:1234"}),
                "api_type": (["openai_compatible", "lmstudio_native"], {"default": "openai_compatible"}),
                "model": (["auto"], {"default": "auto"}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 1024, "min": 1, "max": 32768}),
                "timeout": ("INT", {"default": 120, "min": 1, "max": 3600}),
                "unload_existing_models": ("BOOLEAN", {"default": False}),
                "force_rerun": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("text", "model")
    FUNCTION = "ask"
    CATEGORY = "🎨 DockerCPU API/Utilities"
    DESCRIPTION = "Ask a local or OpenAI-compatible LLM endpoint and return the response text."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time() if kwargs.get("force_rerun") else ""

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def ask(self, endpoint_url, api_type, model, prompt, system_prompt, api_key, temperature, max_tokens, timeout, unload_existing_models=False, force_rerun=False, image=None):
        if api_type not in ("openai_compatible", "lmstudio_native"):
            raise ValueError(f"Unsupported api_type: {api_type}")

        endpoint_url = normalize_endpoint_url(endpoint_url)
        selected_model = (model or "auto").strip()
        if selected_model == "auto":
            models = fetch_models(endpoint_url, api_type, api_key, timeout)
            if not models:
                raise ValueError(f"No models returned for {api_type} from {endpoint_url}")
            selected_model = models[0]

        if api_type == "lmstudio_native":
            if unload_existing_models:
                unload_lmstudio_models(endpoint_url, api_key, timeout)
            selected_model = load_lmstudio_model(endpoint_url, selected_model, api_key, timeout, unload_existing_models)
            payload = build_lmstudio_payload(selected_model, prompt, system_prompt, temperature, max_tokens, image)
            response = requests.post(
                lmstudio_url(endpoint_url, "chat"),
                headers=build_headers(api_key),
                json=payload,
                timeout=timeout,
            )
        else:
            payload = build_openai_payload(selected_model, prompt, system_prompt, temperature, max_tokens, image)
            response = requests.post(
                openai_url(endpoint_url, "chat/completions"),
                headers=build_headers(api_key),
                json=payload,
                timeout=timeout,
            )

        raise_for_status_with_body(response)
        return (extract_response_text(response.json()), selected_model)


NODE_CLASS_MAPPINGS = {
    "LocalLLM": LocalLLM,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LocalLLM": "Local LLM",
}
