# Amazon Bedrock via IAM Roles Anywhere

The Bedrock nodes (`🎨 DockerCPU API/☁️ Bedrock`) authenticate with a named AWS profile. These files set up that profile using IAM Roles Anywhere and an X.509 client certificate, so no long-lived access keys are needed.

```
.env                          AWS_BEDROCK_PROFILE=comfyui-bedrock   (name only)
~/.aws/config                 [profile comfyui-bedrock] credential_process = aws_signing_helper ...
~/.aws/certs/comfyui-bedrock/ ca.pem ca.key client.pem client.key
```

| File | Purpose |
|---|---|
| `bedrock-roles-anywhere.yml` | CloudFormation: trust anchor (your CA), Roles Anywhere profile, `ComfyUIBedrockInferenceRA` role, `ComfyUIBedrockReadOnlyRA` account-wide read-only role for MCP and other tooling (`IncludeReadOnlyRole`, on by default), optional `ComfyUIBedrockManagementRA` role |
| `rolesanywhere.sh` | Creates certs, deploys the stack, writes the `~/.aws/config` profile, tests it |

## Region policy

The roles have **no region restrictions**. The policies use `Resource: "*"` with no `aws:RequestedRegion` condition, so the role can invoke models in any region, directly or through cross-region (`us.`, `eu.`, `apac.`, ...) and `global.` inference profiles. Only the Roles Anywhere trust anchor and profile are regional: they live in the region you deploy to, and `aws_signing_helper` uses that region's endpoint. The credentials it returns work everywhere. An Organizations SCP that denies regions still applies on top of this.

## Setup (Git Bash or Linux)

Prerequisites: AWS CLI v2, [`aws_signing_helper`](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html) on PATH, openssl, and an admin profile that can create IAM roles and Roles Anywhere resources.

```bash
cd aws
./rolesanywhere.sh certs                                   # CA + client cert -> ~/.aws/certs/comfyui-bedrock/
DEPLOY_PROFILE=<admin-profile> ./rolesanywhere.sh deploy   # stack in the admin profile's region (or RA_REGION=...)
DEPLOY_PROFILE=<admin-profile> ./rolesanywhere.sh config   # writes [profile comfyui-bedrock], backs up the config
./rolesanywhere.sh test                                    # identity, model count, one Nova Micro Converse call
```

Or run all four steps at once: `DEPLOY_PROFILE=<admin-profile> ./rolesanywhere.sh all`.

### Deploying from the CloudFormation console instead

Parameter boxes in the console are single-line, so the template does not take the PEM file. Its `CACertificateBody` parameter takes only the base64 between the `BEGIN`/`END CERTIFICATE` lines, joined into one line with no spaces. The template adds the PEM header and footer back. Print the value with `./rolesanywhere.sh body` and paste it as is. Afterwards, run `DEPLOY_PROFILE=<admin-profile> ./rolesanywhere.sh config` to write the profile from the stack outputs. Keep the default stack name `comfyui-bedrock-rolesanywhere`, or set `STACK_NAME`.

Useful options (environment variables): `PROFILE_NAME`, `BEDROCK_REGION` (the profile's default region), `CLIENT_CN`, `STACK_NAME`, and `EXTRA_PARAMS="IncludeModelManagementRole=True AllowMarketplaceSubscribe=False"`.

Then put the profile name in the `.env` that ComfyUI loads (`G:\Ai\.env`, or the repo `.env`):

```
AWS_BEDROCK_PROFILE=comfyui-bedrock
AWS_BEDROCK_REGION=us-east-1        # optional, used when the profile has no region
```

### Renewing the client certificate

The client certificate is valid for 2 years (`CLIENT_DAYS`) and the CA for 10 years. Run `./rolesanywhere.sh client` to issue a new client certificate from the same CA. No stack change is needed.

### Model access

Most serverless models are enabled on first invoke. For third-party models this happens through an AWS Marketplace subscription, which is why the role has `aws-marketplace:Subscribe` by default; turn it off with `AllowMarketplaceSubscribe=False` once your models are enabled. Anthropic models also need the one-time use-case form per account (Bedrock console → Model catalog). Some models can only be called through an inference profile. Pick the `global.` or geographic id in the dropdown.

### Docker / other machines

A machine that only calls Bedrock needs `client.pem` and `client.key`, not `ca.key`. The `credential_process` line holds absolute paths, so give a container its own config that uses container paths and point to it with `AWS_CONFIG_FILE`, rather than mounting the Windows `~/.aws/config` unchanged.

## Nodes

**Bedrock LLM (Converse)**: text or vision chat with any text model or inference profile. Outputs `text`, `reasoning` (extended thinking, when the model returns it), `model` and `usage_json`. Every frame of an optional `image` batch is sent. Set `temperature` or `top_p` to a negative value to leave it out of the request. Model-specific options go in `additional_model_request_fields`, for example `{"thinking": {"type": "enabled", "budget_tokens": 2048}}`.

**Bedrock Invoke Model (JSON)**: any model, called with its native request body. Images returned as `images[]` or `artifacts[].base64` (Nova Canvas, Titan Image, Stability) come out as `IMAGE`. The body supports these placeholders:

- `{{prompt}}` and `{{negative_prompt}}`: inserted JSON-escaped
- `{{seed}}`
- `{{image}}`: the first input image, as base64 PNG
- `{{images}}`: all input images, as a JSON array

The default body is a Nova Canvas text-to-image request.

Both nodes have the same three dropdowns:

- **profile**: `(.env default)` uses `AWS_BEDROCK_PROFILE` when the workflow runs, so a shared workflow follows each machine's `.env`. The other entries are every profile in `~/.aws/config`.
- **region**: `(profile default)` or any Bedrock region.
- **model**: loaded live (`ListFoundationModels` + `ListInferenceProfiles`) for the node's profile and region. `global.` profiles are listed first. To reload it, right-click → *Refresh Bedrock models*. `model_override` accepts any id or ARN, including provisioned, imported and application inference profiles.

Only profile, region and model names are saved in workflows and PNG metadata. No credentials are stored.
