"""
Offline tests for the Bedrock nodes (API/Bedrock/node.py).

AWS calls are replaced with botocore's Stubber, and AWS_CONFIG_FILE points at a temporary
config, so no credentials or network are needed.
"""

import base64
import importlib.util
import io
import json
import os

import numpy as np
import pytest
from PIL import Image

boto3 = pytest.importorskip("boto3")
from botocore.stub import Stubber  # noqa: E402

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE_PATH = os.path.join(PACKAGE_DIR, "API", "Bedrock", "node.py")


@pytest.fixture()
def bedrock(tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.write_text(
        "[profile alpha]\nregion = ap-southeast-2\n"
        "aws_access_key_id = AKIAEXAMPLE\naws_secret_access_key = secret\n\n"
        "[profile beta]\nregion = eu-west-1\n"
        "aws_access_key_id = AKIAEXAMPLE\naws_secret_access_key = secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    monkeypatch.setenv("AWS_BEDROCK_PROFILE", "alpha")
    monkeypatch.delenv("AWS_BEDROCK_REGION", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    spec = importlib.util.spec_from_file_location("bedrock_node_under_test", NODE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_b64(color=(255, 0, 0), size=(8, 8)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_profiles_and_env_default(bedrock):
    assert bedrock.profile_choices() == [bedrock.ENV_PROFILE, "alpha", "beta"]
    assert bedrock.resolve_profile(bedrock.ENV_PROFILE) == "alpha"
    assert bedrock.resolve_profile("beta") == "beta"


def test_region_resolution(bedrock, monkeypatch):
    session = bedrock.get_session("alpha")
    assert bedrock.resolve_region(session, bedrock.PROFILE_REGION) == "ap-southeast-2"
    assert bedrock.resolve_region(session, "us-west-2") == "us-west-2"
    regions = bedrock.region_choices()
    assert regions[0] == bedrock.PROFILE_REGION
    assert {"us-east-1", "eu-central-1", "ap-southeast-2"} <= set(regions)


def test_unknown_profile_message(bedrock):
    with pytest.raises(RuntimeError, match="not found"):
        bedrock.get_session("nope")


def test_fetch_models_orders_profiles_and_filters_text(bedrock):
    client, _ = bedrock.get_client("alpha", "us-east-1", "bedrock", 20)
    with Stubber(client) as stub:
        stub.add_response("list_foundation_models", {"modelSummaries": [
            {"modelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0",
             "modelId": "amazon.nova-lite-v1:0", "outputModalities": ["TEXT"],
             "inferenceTypesSupported": ["ON_DEMAND"], "modelLifecycle": {"status": "ACTIVE"}},
            {"modelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-canvas-v1:0",
             "modelId": "amazon.nova-canvas-v1:0", "outputModalities": ["IMAGE"],
             "inferenceTypesSupported": ["ON_DEMAND"], "modelLifecycle": {"status": "ACTIVE"}},
            {"modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-x-v1:0",
             "modelId": "anthropic.claude-x-v1:0", "outputModalities": ["TEXT"],
             "inferenceTypesSupported": ["INFERENCE_PROFILE"], "modelLifecycle": {"status": "ACTIVE"}},
        ]})
        stub.add_response("list_inference_profiles", {"inferenceProfileSummaries": [
            {"inferenceProfileName": "us claude", "inferenceProfileArn": "arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.anthropic.claude-x-v1:0",
             "inferenceProfileId": "us.anthropic.claude-x-v1:0", "status": "ACTIVE", "type": "SYSTEM_DEFINED",
             "models": [{"modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-x-v1:0"}]},
            {"inferenceProfileName": "global claude", "inferenceProfileArn": "arn:aws:bedrock:us-east-1:111122223333:inference-profile/global.anthropic.claude-x-v1:0",
             "inferenceProfileId": "global.anthropic.claude-x-v1:0", "status": "ACTIVE", "type": "SYSTEM_DEFINED",
             "models": [{"modelArn": "arn:aws:bedrock:::foundation-model/anthropic.claude-x-v1:0"}]},
        ]}, {"typeEquals": "SYSTEM_DEFINED"})
        stub.add_response("list_inference_profiles", {"inferenceProfileSummaries": []}, {"typeEquals": "APPLICATION"})
        models = bedrock.fetch_models("alpha", "us-east-1", "text")
    assert models == ["global.anthropic.claude-x-v1:0", "us.anthropic.claude-x-v1:0", "amazon.nova-lite-v1:0"]


def test_converse_node_with_image(bedrock):
    node = bedrock.BedrockConverse()
    client, _ = bedrock.get_client(bedrock.ENV_PROFILE, "us-west-2", "bedrock-runtime", 300)
    image = np.ones((2, 16, 16, 3), dtype=np.float32) * 0.5
    with Stubber(client) as stub:
        def check(request):
            return True
        stub.add_response("converse", {
            "output": {"message": {"role": "assistant", "content": [
                {"reasoningContent": {"reasoningText": {"text": "thinking"}}},
                {"text": "a grey square"},
            ]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 10, "outputTokens": 3, "totalTokens": 13},
            "metrics": {"latencyMs": 5},
        })
        text, reasoning, model, usage = node.converse(
            bedrock.ENV_PROFILE, "us-west-2", "global.anthropic.claude-x-v1:0", "describe", "be brief",
            -1.0, 100, 300, image=image,
            additional_model_request_fields='{"thinking": {"type": "enabled", "budget_tokens": 1024}}')
    assert text == "a grey square"
    assert reasoning == "thinking"
    assert model == "global.anthropic.claude-x-v1:0"
    assert json.loads(usage)["usage"]["totalTokens"] == 13


def test_build_converse_request(bedrock):
    pil = Image.new("RGB", (4, 4))
    request = bedrock.build_converse_request("m", "hi", "sys", -1, 50, 0.9, [pil, pil], '{"k": 1}', "END\n")
    content = request["messages"][0]["content"]
    assert [list(c)[0] for c in content] == ["image", "image", "text"]
    assert request["inferenceConfig"] == {"maxTokens": 50, "topP": 0.9, "stopSequences": ["END"]}
    assert request["system"] == [{"text": "sys"}]
    assert request["additionalModelRequestFields"] == {"k": 1}
    with pytest.raises(ValueError):
        bedrock.build_converse_request("m", "", "", 0.5, 10)


def test_render_default_body(bedrock):
    body = bedrock.render_body(bedrock.DEFAULT_INVOKE_BODY, 'a "quoted" cat', 42)
    assert body["textToImageParams"]["text"] == 'a "quoted" cat'
    assert body["imageGenerationConfig"]["seed"] == 42
    with pytest.raises(ValueError, match="no image"):
        bedrock.render_body('{"i": "{{image}}"}')


def test_invoke_node_decodes_images(bedrock):
    node = bedrock.BedrockInvokeModel()
    client, _ = bedrock.get_client("beta", bedrock.PROFILE_REGION, "bedrock-runtime", 300)
    from botocore.response import StreamingBody
    payload = json.dumps({"images": [png_b64(), png_b64((0, 255, 0))]}).encode()
    with Stubber(client) as stub:
        stub.add_response("invoke_model", {
            "body": StreamingBody(io.BytesIO(payload), len(payload)),
            "contentType": "application/json",
        })
        images, text, response_json, model = node.invoke(
            "beta", bedrock.PROFILE_REGION, "amazon.nova-canvas-v1:0", bedrock.DEFAULT_INVOKE_BODY, "cat", 1, 300)
    assert tuple(images.shape) == (2, 8, 8, 3)
    assert float(images[0, 0, 0, 0]) == pytest.approx(1.0)
    assert float(images[1, 0, 0, 1]) == pytest.approx(1.0)
    assert len(json.loads(response_json)["images"]) == 2 and text == ""
    assert bedrock.summarize_payload({"images": ["x" * 1000]}) == '{\n  "images": [\n    "<1000 chars>"\n  ]\n}'
    assert client.meta.region_name == "eu-west-1"


def test_extract_text_shapes(bedrock):
    assert bedrock.extract_text({"generation": "g"}) == "g"
    assert bedrock.extract_text({"content": [{"type": "text", "text": "c"}]}) == "c"
    assert bedrock.extract_text({"output": {"message": {"content": [{"text": "n"}]}}}) == "n"
    assert bedrock.extract_text({"results": [{"outputText": "t"}]}) == "t"
