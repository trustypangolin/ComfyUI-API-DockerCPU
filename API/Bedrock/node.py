"""
Amazon Bedrock nodes for ComfyUI-API-DockerCPU.

Credentials come from a named AWS profile in ~/.aws/config (or AWS_CONFIG_FILE), normally an
IAM Roles Anywhere `credential_process` profile created by aws/rolesanywhere.sh. Nothing secret is
stored in the workflow: only the profile name, region and model id.

- profile "(.env default)" resolves at run time to AWS_BEDROCK_PROFILE (environment, then the repo
  .env), so shared workflows follow each machine's .env. Any other entry is a profile from the config.
- region "(profile default)" uses the profile's region, then AWS_BEDROCK_REGION, then us-east-1.
  Every Bedrock region is selectable; nothing is restricted.

Nodes:
- BedrockConverse     text / vision chat via the Converse API (any text-output model or inference profile)
- BedrockInvokeModel  raw InvokeModel with a JSON body; decodes returned images (Nova Canvas, Titan, Stability...)
"""

import base64
import json
import os
import threading
import time
from io import BytesIO

import numpy as np
from PIL import Image

try:
    import torch
except Exception:  # tests / tooling without torch
    torch = None

try:
    import boto3
    import botocore.session
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO_AVAILABLE = True
except Exception:
    boto3 = None
    BOTO_AVAILABLE = False
    BotoCoreError = ClientError = Exception

try:
    from aiohttp import web
    from server import PromptServer
    ROUTES_AVAILABLE = True
except Exception:
    web = None
    PromptServer = None
    ROUTES_AVAILABLE = False


LOG_PREFIX = "[ComfyUI-API-DockerCPU] Bedrock:"
CATEGORY = "🎨 DockerCPU API/☁️ Bedrock"

ENV_PROFILE = "(.env default)"
PROFILE_REGION = "(profile default)"
PROFILE_ENV_VARS = ("AWS_BEDROCK_PROFILE",)
REGION_ENV_VARS = ("AWS_BEDROCK_REGION",)
FALLBACK_REGION = "us-east-1"

# Commercial regions with (or likely to get) Bedrock. Merged with botocore's endpoint data; any
# other region typed into a workflow is accepted too (VALIDATE_INPUTS skips combo checks).
BEDROCK_REGIONS = [
    "af-south-1",
    "ap-east-2",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ap-south-1", "ap-south-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-4", "ap-southeast-5", "ap-southeast-7",
    "ca-central-1", "ca-west-1",
    "eu-central-1", "eu-central-2",
    "eu-north-1",
    "eu-south-1", "eu-south-2",
    "eu-west-1", "eu-west-2", "eu-west-3",
    "il-central-1",
    "me-central-1", "me-south-1",
    "mx-central-1",
    "sa-east-1",
    "us-east-1", "us-east-2",
    "us-west-1", "us-west-2",
    "us-gov-east-1", "us-gov-west-1",
]

# Shown until the live list for the default profile/region has been fetched.
FALLBACK_TEXT_MODELS = [
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0",
]
FALLBACK_ALL_MODELS = FALLBACK_TEXT_MODELS + [
    "amazon.nova-canvas-v1:0",
    "amazon.titan-image-generator-v2:0",
    "stability.sd3-5-large-v1:0",
]

DEFAULT_INVOKE_BODY = json.dumps({
    "taskType": "TEXT_IMAGE",
    "textToImageParams": {"text": "{{prompt}}"},
    "imageGenerationConfig": {
        "numberOfImages": 1,
        "width": 1024,
        "height": 1024,
        "cfgScale": 6.5,
        "seed": "{{seed}}",
    },
}, indent=2).replace('"{{seed}}"', "{{seed}}")

CONVERSE_MAX_IMAGE_BYTES = 3_750_000


# ---------------------------------------------------------------------------------------------
# .env / profile / region resolution
# ---------------------------------------------------------------------------------------------

# Repo-root .env (gitignored), read only for variables missing from the environment.
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")


def _read_env_file(names):
    wanted = {n.upper(): n for n in names}
    found = {}
    if not os.path.isfile(ENV_FILE):
        return found
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key.lower().startswith("export "):
                    key = key[7:].strip()
                value = value.strip().strip("'\"")
                if key.upper() in wanted and value:
                    found.setdefault(wanted[key.upper()], value)
    except OSError:
        pass
    return found


def _first_env(names):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    from_file = _read_env_file(names)
    for name in names:
        value = from_file.get(name, "").strip()
        if value:
            return value
    return ""


def env_profile():
    return _first_env(PROFILE_ENV_VARS)


def aws_config_path():
    return os.path.expanduser(os.environ.get("AWS_CONFIG_FILE") or os.path.join("~", ".aws", "config"))


def _config_stamp():
    """Changes when ~/.aws/config (or credentials) is edited, so cached sessions are rebuilt."""
    stamp = []
    for path in (aws_config_path(),
                 os.path.expanduser(os.environ.get("AWS_SHARED_CREDENTIALS_FILE") or "~/.aws/credentials")):
        try:
            stamp.append(os.path.getmtime(path))
        except OSError:
            stamp.append(0)
    return tuple(stamp)


def list_profiles():
    if not BOTO_AVAILABLE:
        return []
    try:
        return sorted(botocore.session.Session().available_profiles, key=str.lower)
    except Exception as e:
        print(f"{LOG_PREFIX} could not read AWS profiles from {aws_config_path()}: {e}")
        return []


def profile_choices():
    return [ENV_PROFILE] + [p for p in list_profiles() if p != ENV_PROFILE]


def region_choices():
    regions = set(BEDROCK_REGIONS)
    if BOTO_AVAILABLE:
        try:
            regions.update(boto3.session.Session().get_available_regions("bedrock-runtime"))
        except Exception:
            pass
    return [PROFILE_REGION] + sorted(regions)


def resolve_profile(profile):
    """Profile name to use, or None for boto3's default credential chain."""
    profile = (profile or "").strip()
    if not profile or profile == ENV_PROFILE:
        return env_profile() or None
    return profile


# ---------------------------------------------------------------------------------------------
# Sessions and clients (cached; credential_process credentials refresh automatically)
# ---------------------------------------------------------------------------------------------

_client_lock = threading.Lock()
_sessions = {}
_clients = {}
_stamp = None


def _require_boto():
    if not BOTO_AVAILABLE:
        raise RuntimeError("boto3 is not installed. Run: pip install -r requirements.txt (needs boto3>=1.35)")


def get_session(profile):
    """boto3 Session for a resolved profile name (None = default chain)."""
    global _stamp
    _require_boto()
    with _client_lock:
        stamp = _config_stamp()
        if stamp != _stamp:
            _sessions.clear()
            _clients.clear()
            _stamp = stamp
        if profile not in _sessions:
            try:
                _sessions[profile] = boto3.session.Session(profile_name=profile)
            except Exception as e:
                known = ", ".join(list_profiles()) or "none"
                raise RuntimeError(
                    f"AWS profile '{profile}' not found in {aws_config_path()} (profiles: {known}). "
                    "Set AWS_BEDROCK_PROFILE in .env or pick a profile on the node."
                ) from e
        return _sessions[profile]


def resolve_region(session, region):
    region = (region or "").strip()
    if region and region != PROFILE_REGION:
        return region
    return session.region_name or _first_env(REGION_ENV_VARS) or FALLBACK_REGION


def get_client(profile, region, service="bedrock-runtime", timeout=300):
    """(client, resolved_region) for the given node inputs."""
    session = get_session(resolve_profile(profile))
    region = resolve_region(session, region)
    key = (session.profile_name, region, service, int(timeout))
    with _client_lock:
        client = _clients.get(key)
        if client is None:
            client = session.client(service, region_name=region, config=Config(
                connect_timeout=10,
                read_timeout=int(timeout),
                retries={"max_attempts": 4, "mode": "adaptive"},
                user_agent_extra="ComfyUI-API-DockerCPU",
            ))
            _clients[key] = client
    return client, region


def describe_error(e, profile, region, model=None):
    where = f"profile={resolve_profile(profile) or '(default chain)'} region={region}"
    if model:
        where += f" model={model}"
    if isinstance(e, ClientError):
        err = e.response.get("Error", {})
        code, msg = err.get("Code", "Error"), err.get("Message", str(e))
        hint = ""
        if code in ("AccessDeniedException",) and "model" in msg.lower():
            hint = (" Hint: the model may need access enabled/first-use form in this region, or use a "
                    "cross-region/global inference profile id (e.g. 'global.' / 'us.' prefix).")
        elif code == "ValidationException" and "on-demand throughput" in msg.lower():
            hint = " Hint: this model must be called through an inference profile (pick a 'global.'/'us.'/'eu.'/'apac.' id)."
        return RuntimeError(f"Bedrock {code} ({where}): {msg}{hint}")
    text = str(e)
    if "credential" in text.lower() or "process" in text.lower():
        text += (" - check the profile's credential_process (aws_signing_helper path, client.pem/client.key "
                 "paths) with: aws sts get-caller-identity --profile <name>")
    return RuntimeError(f"Bedrock call failed ({where}): {text}")


# ---------------------------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------------------------

MODEL_LIST_TTL = 600
_model_cache = {}
_model_cache_lock = threading.Lock()
_refreshing = set()


def _paged(call, key, **kwargs):
    token = None
    while True:
        page = call(**kwargs, **({"nextToken": token} if token else {}))
        yield from page.get(key, [])
        token = page.get("nextToken")
        if not token:
            return


def fetch_models(profile, region, kind="text"):
    """Invocable model ids: inference profiles (global./us./eu./apac./... and application profiles)
    first, then on-demand foundation models. kind="text" keeps text-output models (Converse)."""
    bedrock, region = get_client(profile, region, "bedrock", timeout=20)
    modalities = {}
    on_demand = []
    for m in bedrock.list_foundation_models().get("modelSummaries", []):
        modalities[m["modelId"]] = set(m.get("outputModalities") or [])
        if "ON_DEMAND" in (m.get("inferenceTypesSupported") or []):
            if kind != "text" or "TEXT" in modalities[m["modelId"]]:
                on_demand.append((m.get("modelLifecycle", {}).get("status") == "LEGACY", m["modelId"]))

    def is_wanted(profile_summary):
        if kind != "text":
            return True
        for model in profile_summary.get("models") or []:
            base = model.get("modelArn", "").rsplit("/", 1)[-1]
            if "TEXT" in modalities.get(base, {"TEXT"}):
                return True
        return False

    profiles = []
    try:
        for p in _paged(bedrock.list_inference_profiles, "inferenceProfileSummaries", typeEquals="SYSTEM_DEFINED"):
            if p.get("status", "ACTIVE") == "ACTIVE" and is_wanted(p):
                profiles.append(p["inferenceProfileId"])
        for p in _paged(bedrock.list_inference_profiles, "inferenceProfileSummaries", typeEquals="APPLICATION"):
            if p.get("status", "ACTIVE") == "ACTIVE" and is_wanted(p):
                profiles.append(p["inferenceProfileArn"])
    except ClientError as e:
        print(f"{LOG_PREFIX} list_inference_profiles failed in {region}: {e}")

    # global. first, then geo profiles, then plain models (legacy last)
    profiles.sort(key=lambda i: (not i.startswith("global."), i.startswith("arn:"), i))
    models = [m for _, m in sorted(on_demand)]
    seen, out = set(), []
    for model_id in profiles + models:
        if model_id not in seen:
            seen.add(model_id)
            out.append(model_id)
    return out


def cached_models(profile, region, kind, refresh=False):
    key = (resolve_profile(profile), region, kind)
    with _model_cache_lock:
        hit = _model_cache.get(key)
        if hit and not refresh and time.monotonic() - hit[0] < MODEL_LIST_TTL:
            return hit[1]
    models = fetch_models(profile, region, kind)
    with _model_cache_lock:
        _model_cache[key] = (time.monotonic(), models)
    return models


def _background_refresh(kind):
    key = (resolve_profile(ENV_PROFILE), PROFILE_REGION, kind)
    with _model_cache_lock:
        if key in _refreshing:
            return
        _refreshing.add(key)

    def run():
        try:
            cached_models(ENV_PROFILE, PROFILE_REGION, kind, refresh=True)
        except Exception as e:
            print(f"{LOG_PREFIX} model list refresh failed: {e}")
        finally:
            with _model_cache_lock:
                _refreshing.discard(key)

    threading.Thread(target=run, daemon=True, name=f"bedrock-models-{kind}").start()


def model_choices(kind):
    """Server-side combo values. Never blocks /object_info: returns the cached list for the .env
    profile + its default region (fetching it in the background when stale), else a static list.
    The UI refreshes the list for the node's own profile/region."""
    fallback = FALLBACK_TEXT_MODELS if kind == "text" else FALLBACK_ALL_MODELS
    if not BOTO_AVAILABLE:
        return list(fallback)
    key = (resolve_profile(ENV_PROFILE), PROFILE_REGION, kind)
    with _model_cache_lock:
        hit = _model_cache.get(key)
    if not hit or time.monotonic() - hit[0] >= MODEL_LIST_TTL:
        _background_refresh(kind)
    if hit and hit[1]:
        return list(hit[1])
    return list(fallback)


# ---------------------------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------------------------

def tensor_to_pils(image):
    """ComfyUI IMAGE (B,H,W,C float 0-1) -> list of RGB PIL images."""
    if image is None:
        return []
    if torch is not None and isinstance(image, torch.Tensor):
        array = image.detach().cpu().numpy()
    else:
        array = np.asarray(image)
    if array.ndim == 3:
        array = array[None]
    out = []
    for frame in array:
        frame = (np.clip(frame, 0.0, 1.0) * 255).round().astype(np.uint8)
        if frame.shape[-1] == 1:
            frame = frame[..., 0]
        out.append(Image.fromarray(frame).convert("RGB"))
    return out


def pil_to_bytes(pil, limit=None):
    """(format, bytes): PNG, or JPEG when the PNG is over `limit`."""
    buffer = BytesIO()
    pil.save(buffer, format="PNG")
    data = buffer.getvalue()
    if limit and len(data) > limit:
        for quality in (92, 85, 75, 60):
            buffer = BytesIO()
            pil.save(buffer, format="JPEG", quality=quality)
            data = buffer.getvalue()
            if len(data) <= limit:
                return "jpeg", data
        return "jpeg", data
    return "png", data


def pils_to_tensor(pils):
    if not pils:
        return blank_image()
    size = pils[0].size
    frames = []
    for pil in pils:
        pil = pil.convert("RGB")
        if pil.size != size:
            pil = pil.resize(size, Image.LANCZOS)
        frames.append(np.asarray(pil).astype(np.float32) / 255.0)
    array = np.stack(frames)
    return torch.from_numpy(array) if torch is not None else array


def blank_image():
    array = np.zeros((1, 64, 64, 3), dtype=np.float32)
    return torch.from_numpy(array) if torch is not None else array


# ---------------------------------------------------------------------------------------------
# Converse
# ---------------------------------------------------------------------------------------------

def build_converse_request(model_id, prompt, system_prompt, temperature, max_tokens, top_p=-1.0,
                           images=None, additional_fields="", stop_sequences=""):
    content = []
    for pil in images or []:
        fmt, data = pil_to_bytes(pil, CONVERSE_MAX_IMAGE_BYTES)
        content.append({"image": {"format": fmt, "source": {"bytes": data}}})
    if (prompt or "").strip():
        content.append({"text": prompt})
    if not content:
        raise ValueError("Bedrock Converse needs a prompt and/or an image.")

    inference = {"maxTokens": int(max_tokens)}
    # Negative = omit (some models reject temperature with top_p, or with extended thinking)
    if temperature is not None and temperature >= 0:
        inference["temperature"] = float(temperature)
    if top_p is not None and top_p >= 0:
        inference["topP"] = float(top_p)
    stops = [s for s in (stop_sequences or "").splitlines() if s]
    if stops:
        inference["stopSequences"] = stops

    request = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": content}],
        "inferenceConfig": inference,
    }
    if (system_prompt or "").strip():
        request["system"] = [{"text": system_prompt}]
    if (additional_fields or "").strip():
        try:
            request["additionalModelRequestFields"] = json.loads(additional_fields)
        except json.JSONDecodeError as e:
            raise ValueError(f"additional_model_request_fields is not valid JSON: {e}") from e
    return request


def parse_converse_response(response):
    blocks = response.get("output", {}).get("message", {}).get("content", []) or []
    texts, reasoning = [], []
    for block in blocks:
        if "text" in block:
            texts.append(block["text"])
        elif "reasoningContent" in block:
            r = block["reasoningContent"].get("reasoningText", {}).get("text")
            if r:
                reasoning.append(r)
    stop = response.get("stopReason")
    text = "\n".join(texts).strip()
    if not text:
        hint = " Raise max_tokens." if stop == "max_tokens" else ""
        raise ValueError(f"Bedrock returned no text (stopReason={stop}).{hint}")
    meta = {"stopReason": stop, "usage": response.get("usage"), "metrics": response.get("metrics")}
    return text, "\n".join(reasoning), json.dumps(meta, default=str)


# ---------------------------------------------------------------------------------------------
# InvokeModel
# ---------------------------------------------------------------------------------------------

def render_body(body, prompt="", seed=0, images=None, negative_prompt=""):
    """Fill {{prompt}}, {{negative_prompt}}, {{seed}}, {{image}} (first image, base64 PNG) and
    {{images}} (JSON array of base64 PNGs) placeholders, then parse as JSON."""
    b64 = [base64.b64encode(pil_to_bytes(p)[1]).decode("ascii") for p in images or []]
    if ("{{image}}" in body or "{{images}}" in body) and not b64:
        raise ValueError("The body uses {{image}}/{{images}} but no image is connected.")
    text = (body
            .replace("{{prompt}}", json.dumps(prompt or "")[1:-1])
            .replace("{{negative_prompt}}", json.dumps(negative_prompt or "")[1:-1])
            .replace("{{seed}}", str(int(seed)))
            .replace("{{images}}", json.dumps(b64))
            .replace("{{image}}", b64[0] if b64 else ""))
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Request body is not valid JSON after placeholders: {e}") from e


def _decode_b64_image(value):
    if not isinstance(value, str) or len(value) < 64:
        return None
    if value.startswith("data:") and "," in value:
        value = value.split(",", 1)[1]
    try:
        return Image.open(BytesIO(base64.b64decode(value, validate=False))).convert("RGB")
    except Exception:
        return None


def extract_images(payload):
    """Images from common Bedrock response shapes: images[] (Nova Canvas, Titan, Stability SD3/Ultra),
    artifacts[].base64 (older Stability), image (str)."""
    pils = []
    for item in payload.get("images") or []:
        pil = _decode_b64_image(item if isinstance(item, str) else (item or {}).get("base64") or (item or {}).get("image"))
        if pil:
            pils.append(pil)
    for item in payload.get("artifacts") or []:
        if isinstance(item, dict):
            pil = _decode_b64_image(item.get("base64"))
            if pil:
                pils.append(pil)
    if isinstance(payload.get("image"), str):
        pil = _decode_b64_image(payload["image"])
        if pil:
            pils.append(pil)
    return pils


def extract_text(payload):
    for key in ("outputText", "generation", "completion", "text"):
        if isinstance(payload.get(key), str):
            return payload[key]
    content = payload.get("content")
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        if any(parts):
            return "\n".join(parts)
    message = (payload.get("output") or {}).get("message") if isinstance(payload.get("output"), dict) else None
    if message:
        return "\n".join(c.get("text", "") for c in message.get("content", []) if isinstance(c, dict))
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        return msg.get("content") or choices[0].get("text") or ""
    results = payload.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        return results[0].get("outputText", "")
    return ""


def summarize_payload(payload):
    """Response JSON with base64 blobs shortened, for the 'response' output."""
    def shrink(value):
        if isinstance(value, str) and len(value) > 512:
            return f"<{len(value)} chars>"
        if isinstance(value, list):
            return [shrink(v) for v in value]
        if isinstance(value, dict):
            return {k: shrink(v) for k, v in value.items()}
        return value
    return json.dumps(shrink(payload), indent=2, default=str)


# ---------------------------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------------------------

def _common_inputs(kind):
    return {
        "profile": (profile_choices(), {
            "default": ENV_PROFILE,
            "tooltip": "AWS profile from ~/.aws/config. '(.env default)' uses AWS_BEDROCK_PROFILE from the "
                       "environment / .env, so the workflow follows each machine's setting.",
        }),
        "region": (region_choices(), {
            "default": PROFILE_REGION,
            "tooltip": "Any Bedrock region. '(profile default)' uses the profile's region, then AWS_BEDROCK_REGION, "
                       "then us-east-1. 'global.' inference profiles route across all commercial regions.",
        }),
        "model": (model_choices(kind), {
            "tooltip": "Model id or inference profile id. The list is loaded live for the selected profile and region.",
        }),
    }


class _BedrockBase:
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time() if kwargs.get("force_rerun") else ""

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # Skip combo validation: model/region/profile lists are per machine and per region.
        return True

    @staticmethod
    def _model_id(model, model_override):
        model_id = (model_override or "").strip() or (model or "").strip()
        if not model_id:
            raise ValueError("No Bedrock model selected.")
        return model_id


class BedrockConverse(_BedrockBase):
    @classmethod
    def INPUT_TYPES(cls):
        inputs = _common_inputs("text")
        inputs.update({
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "system_prompt": ("STRING", {"multiline": True, "default": ""}),
            "temperature": ("FLOAT", {"default": 0.7, "min": -1.0, "max": 2.0, "step": 0.05,
                                      "tooltip": "Negative = don't send (needed for some models, e.g. with extended thinking)."}),
            "max_tokens": ("INT", {"default": 2048, "min": 1, "max": 128000}),
            "timeout": ("INT", {"default": 300, "min": 10, "max": 3600}),
            "force_rerun": ("BOOLEAN", {"default": False}),
        })
        return {
            "required": inputs,
            "optional": {
                "image": ("IMAGE", {"tooltip": "Every frame of the batch is sent (vision models)."}),
                "model_override": ("STRING", {"default": "",
                                              "tooltip": "Any model id / inference profile / ARN; overrides 'model'."}),
                "top_p": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.01,
                                    "tooltip": "Negative = don't send."}),
                "stop_sequences": ("STRING", {"multiline": True, "default": "", "tooltip": "One per line."}),
                "additional_model_request_fields": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": 'Model-specific JSON, e.g. {"thinking": {"type": "enabled", "budget_tokens": 2048}} '
                               "for Claude extended thinking (set temperature to -1).",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("text", "reasoning", "model", "usage_json")
    FUNCTION = "converse"
    CATEGORY = CATEGORY
    DESCRIPTION = "Chat / vision with any Amazon Bedrock text model using the Converse API, via an AWS profile."

    def converse(self, profile, region, model, prompt, system_prompt, temperature, max_tokens, timeout,
                 force_rerun=False, image=None, model_override="", top_p=-1.0, stop_sequences="",
                 additional_model_request_fields=""):
        model_id = self._model_id(model, model_override)
        client, resolved_region = get_client(profile, region, "bedrock-runtime", timeout)
        request = build_converse_request(model_id, prompt, system_prompt, temperature, max_tokens, top_p,
                                         tensor_to_pils(image), additional_model_request_fields, stop_sequences)
        try:
            response = client.converse(**request)
        except (ClientError, BotoCoreError) as e:
            raise describe_error(e, profile, resolved_region, model_id) from e
        text, reasoning, usage = parse_converse_response(response)
        return (text, reasoning, model_id, usage)


class BedrockInvokeModel(_BedrockBase):
    @classmethod
    def INPUT_TYPES(cls):
        inputs = _common_inputs("all")
        inputs["model"][1]["default"] = "amazon.nova-canvas-v1:0"
        inputs.update({
            "body": ("STRING", {
                "multiline": True, "default": DEFAULT_INVOKE_BODY,
                "tooltip": "Model-native JSON request. Placeholders: {{prompt}}, {{negative_prompt}}, {{seed}}, "
                           "{{image}} (first input image, base64 PNG), {{images}} (JSON array).",
            }),
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            # 858993459 is Nova Canvas / Titan Image's maximum; Stability accepts it too
            "seed": ("INT", {"default": 0, "min": 0, "max": 858993459, "control_after_generate": True}),
            "timeout": ("INT", {"default": 300, "min": 10, "max": 3600}),
            "force_rerun": ("BOOLEAN", {"default": False}),
        })
        return {
            "required": inputs,
            "optional": {
                "image": ("IMAGE",),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "model_override": ("STRING", {"default": "",
                                              "tooltip": "Any model id / inference profile / ARN; overrides 'model'."}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "text", "response_json", "model")
    FUNCTION = "invoke"
    CATEGORY = CATEGORY
    DESCRIPTION = ("Call any Amazon Bedrock model with its native JSON body (InvokeModel). Returned images "
                   "(Nova Canvas, Titan Image, Stability) are decoded to IMAGE; text is extracted when present.")

    def invoke(self, profile, region, model, body, prompt, seed, timeout, force_rerun=False,
               image=None, negative_prompt="", model_override=""):
        model_id = self._model_id(model, model_override)
        client, resolved_region = get_client(profile, region, "bedrock-runtime", timeout)
        request = render_body(body, prompt, seed, tensor_to_pils(image), negative_prompt)
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request).encode("utf-8"),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
        except (ClientError, BotoCoreError) as e:
            raise describe_error(e, profile, resolved_region, model_id) from e

        pils = extract_images(payload)
        text = extract_text(payload)
        if not pils and not text:
            error = payload.get("error") or payload.get("message") or payload.get("finish_reasons")
            if error:
                raise RuntimeError(f"Bedrock {model_id} returned no output: {error}")
        return (pils_to_tensor(pils), text, summarize_payload(payload), model_id)


# ---------------------------------------------------------------------------------------------
# Routes for the UI (model / profile lists)
# ---------------------------------------------------------------------------------------------

if ROUTES_AVAILABLE:
    import asyncio

    @PromptServer.instance.routes.get("/dockercpu/bedrock/models")
    async def get_bedrock_models(request):
        profile = request.query.get("profile", ENV_PROFILE)
        region = request.query.get("region", PROFILE_REGION)
        kind = "all" if request.query.get("kind") == "all" else "text"
        refresh = request.query.get("refresh") == "1"
        loop = asyncio.get_running_loop()
        try:
            models = await loop.run_in_executor(None, cached_models, profile, region, kind, refresh)
            return web.json_response({"models": models})
        except Exception as e:
            region_name = region
            try:
                region_name = resolve_region(get_session(resolve_profile(profile)), region)
            except Exception:
                pass
            err = describe_error(e, profile, region_name) if not isinstance(e, RuntimeError) else e
            return web.json_response({"error": str(err), "models": []}, status=500)

    @PromptServer.instance.routes.get("/dockercpu/bedrock/profiles")
    async def get_bedrock_profiles(request):
        return web.json_response({"profiles": profile_choices(), "env_profile": env_profile()})


NODE_CLASS_MAPPINGS = {
    "BedrockConverse": BedrockConverse,
    "BedrockInvokeModel": BedrockInvokeModel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BedrockConverse": "Bedrock LLM (Converse)",
    "BedrockInvokeModel": "Bedrock Invoke Model (JSON)",
}
