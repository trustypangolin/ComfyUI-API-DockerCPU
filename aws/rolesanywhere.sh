#!/usr/bin/env bash
#====================================================================================================
# IAM Roles Anywhere setup for the ComfyUI Bedrock nodes.
#
#   ./rolesanywhere.sh certs     Create CA + client cert in ~/.aws/certs/comfyui-bedrock/ (once)
#   ./rolesanywhere.sh client    Re-issue only the client cert from the existing CA (renewal)
#   ./rolesanywhere.sh body      Print the CACertificateBody value to paste into the CloudFormation console
#   ./rolesanywhere.sh deploy    Deploy/update the CloudFormation stack (needs an admin profile)
#   ./rolesanywhere.sh config    Write/replace the [profile ...] block in ~/.aws/config from stack outputs
#   ./rolesanywhere.sh test      Check the profile: caller identity, model list, one Converse call
#   ./rolesanywhere.sh all       certs (if missing) + deploy + config + test
#
# Settings (environment variables):
#   DEPLOY_PROFILE  AWS profile with IAM + Roles Anywhere + CloudFormation rights   (deploy/config)
#   RA_REGION       Region for the trust anchor/profile   (default: DEPLOY_PROFILE's region)
#   PROFILE_NAME    Client profile written to ~/.aws/config   (default: comfyui-bedrock)
#   BEDROCK_REGION  Default region stored in that profile     (default: RA_REGION). Any region works.
#   CERT_DIR        (default: ~/.aws/certs/comfyui-bedrock)
#   CLIENT_CN       (default: comfyui-bedrock)   must match the stack's ClientCertificateCN
#   STACK_NAME      (default: comfyui-bedrock-rolesanywhere)
#   EXTRA_PARAMS    Extra "Key=Value" overrides for deploy, e.g. "IncludeModelManagementRole=True"
#   TEST_MODEL      Model/inference profile for the test Converse call (default: amazon.nova-micro-v1:0)
#
# Works in Git Bash on Windows (paths are written as C:/... for aws_signing_helper) and on Linux/macOS.
#====================================================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/bedrock-roles-anywhere.yml"

AWS_DIR="${AWS_DIR:-$HOME/.aws}"
AWS_CONFIG="${AWS_CONFIG_FILE:-$AWS_DIR/config}"
CERT_DIR="${CERT_DIR:-$AWS_DIR/certs/comfyui-bedrock}"
CLIENT_CN="${CLIENT_CN:-comfyui-bedrock}"
PROFILE_NAME="${PROFILE_NAME:-comfyui-bedrock}"
STACK_NAME="${STACK_NAME:-comfyui-bedrock-rolesanywhere}"
DEPLOY_PROFILE="${DEPLOY_PROFILE:-}"
EXTRA_PARAMS="${EXTRA_PARAMS:-}"
TEST_MODEL="${TEST_MODEL:-amazon.nova-micro-v1:0}"
CA_DAYS="${CA_DAYS:-3650}"
CLIENT_DAYS="${CLIENT_DAYS:-730}"

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

# Path as the native OS sees it (C:/Users/... under Git Bash, unchanged elsewhere)
native() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi; }

# Git Bash rewrites "/CN=..." arguments into Windows paths; this turns that off for openssl subjects.
# With conversion off, every path handed to native tools (openssl.exe, aws.exe) must already be native.
export MSYS_NO_PATHCONV=1
CERT_DIR="$(native "$CERT_DIR")"
AWS_CONFIG="$(native "$AWS_CONFIG")"

deploy_args() {
    [ -n "$DEPLOY_PROFILE" ] || die "Set DEPLOY_PROFILE to an admin profile, e.g. DEPLOY_PROFILE=bedrock $0 $1"
    if [ -z "${RA_REGION:-}" ]; then
        RA_REGION="$(aws configure get region --profile "$DEPLOY_PROFILE" || true)"
        [ -n "$RA_REGION" ] || die "Set RA_REGION (profile $DEPLOY_PROFILE has no region)"
    fi
    AWS_ARGS=(--profile "$DEPLOY_PROFILE" --region "$RA_REGION")
}

#----------------------------------------------------------------------------------------------------
write_ext() {
    cat > "$CERT_DIR/openssl-ext.cnf" <<'EOF'
[ v3_ca ]
basicConstraints       = critical, CA:TRUE
keyUsage               = critical, keyCertSign, cRLSign, digitalSignature
subjectKeyIdentifier   = hash

[ v3_client ]
basicConstraints       = critical, CA:FALSE
keyUsage               = critical, digitalSignature
extendedKeyUsage       = clientAuth
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid,issuer
EOF
}

issue_client() {
    [ -f "$CERT_DIR/ca.pem" ] && [ -f "$CERT_DIR/ca.key" ] || die "No CA in $CERT_DIR. Run: $0 certs"
    write_ext
    info "Issuing client certificate CN=$CLIENT_CN ($CLIENT_DAYS days)"
    openssl ecparam -name prime256v1 -genkey -noout -out "$CERT_DIR/client.key.new"
    openssl req -new -key "$CERT_DIR/client.key.new" -subj "/C=AU/O=ComfyUI/CN=$CLIENT_CN" \
        -out "$CERT_DIR/client.csr"
    openssl x509 -req -in "$CERT_DIR/client.csr" -CA "$CERT_DIR/ca.pem" -CAkey "$CERT_DIR/ca.key" \
        -CAcreateserial -days "$CLIENT_DAYS" -sha256 \
        -extfile "$CERT_DIR/openssl-ext.cnf" -extensions v3_client -out "$CERT_DIR/client.pem.new"
    mv -f "$CERT_DIR/client.key.new" "$CERT_DIR/client.key"
    mv -f "$CERT_DIR/client.pem.new" "$CERT_DIR/client.pem"
    rm -f "$CERT_DIR/client.csr"
    chmod 600 "$CERT_DIR/client.key" || true
    openssl verify -CAfile "$CERT_DIR/ca.pem" "$CERT_DIR/client.pem"
    openssl x509 -in "$CERT_DIR/client.pem" -noout -subject -enddate
}

cmd_certs() {
    mkdir -p "$CERT_DIR"
    chmod 700 "$CERT_DIR" || true
    if [ -f "$CERT_DIR/ca.key" ]; then
        info "CA already exists in $CERT_DIR (delete it first to start over). Keeping it."
    else
        write_ext
        info "Creating CA ($CA_DAYS days) in $CERT_DIR"
        openssl ecparam -name prime256v1 -genkey -noout -out "$CERT_DIR/ca.key"
        chmod 600 "$CERT_DIR/ca.key" || true
        openssl req -x509 -new -key "$CERT_DIR/ca.key" -sha256 -days "$CA_DAYS" \
            -subj "/C=AU/O=ComfyUI/CN=ComfyUI Bedrock RolesAnywhere CA" \
            -config "$CERT_DIR/openssl-ext.cnf" -extensions v3_ca -out "$CERT_DIR/ca.pem"
    fi
    if [ -f "$CERT_DIR/client.pem" ]; then
        info "Client certificate already exists. Use '$0 client' to re-issue it."
    else
        issue_client
    fi
    echo
    echo "Keep ca.key off machines that only need to call Bedrock: they need client.pem + client.key only."
}

# CA certificate base64 on one line: the CACertificateBody parameter (console-pasteable)
ca_body() {
    [ -f "$CERT_DIR/ca.pem" ] || die "No $CERT_DIR/ca.pem. Run: $0 certs"
    grep -v -- '-----' "$CERT_DIR/ca.pem" | tr -d ' \r\n'
}

cmd_deploy() {
    deploy_args deploy
    [ -f "$CERT_DIR/ca.pem" ] || die "No $CERT_DIR/ca.pem. Run: $0 certs"
    info "Deploying stack $STACK_NAME to $RA_REGION with profile $DEPLOY_PROFILE"
    # shellcheck disable=SC2086
    aws cloudformation deploy "${AWS_ARGS[@]}" \
        --stack-name "$STACK_NAME" \
        --template-file "$(native "$TEMPLATE")" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset \
        --parameter-overrides "CACertificateBody=$(ca_body)" "ClientCertificateCN=$CLIENT_CN" $EXTRA_PARAMS
    aws cloudformation describe-stacks "${AWS_ARGS[@]}" --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs" --output table
}

stack_output() {
    aws cloudformation describe-stacks "${AWS_ARGS[@]}" --stack-name "$STACK_NAME" \
        --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

# Replace (or append) one [profile NAME] section in an INI file, keeping everything else.
replace_profile_section() {
    local file="$1" name="$2" block="$3" tmp
    tmp="$(mktemp)"
    if [ -f "$file" ]; then
        awk -v hdr="[profile $name]" '
            { line = $0; sub(/\r$/, "", line) }
            line ~ /^[ \t]*\[/ { t = line; gsub(/^[ \t]+|[ \t]+$/, "", t); skip = (t == hdr) }
            !skip { print }
        ' "$file" > "$tmp"
        # drop trailing blank lines before appending
        sed -i -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}' "$tmp" 2>/dev/null || true
        printf '\n' >> "$tmp"
    fi
    printf '%s\n' "$block" >> "$tmp"
    mv -f "$tmp" "$file"
}

cmd_config() {
    deploy_args config
    local ta pa ra helper region block
    ta="$(stack_output TrustAnchorArn)"
    pa="$(stack_output ProfileArn)"
    ra="${ROLE_ARN:-$(stack_output BedrockInferenceRoleArn)}"
    [ -n "$ta" ] && [ "$ta" != "None" ] || die "Stack $STACK_NAME has no outputs. Run: $0 deploy"
    helper="$(command -v aws_signing_helper || true)"
    [ -n "$helper" ] || die "aws_signing_helper not on PATH: https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html"
    region="${BEDROCK_REGION:-$RA_REGION}"
    # credential_process must stay on ONE line
    block="[profile $PROFILE_NAME]
credential_process = $(native "$helper") credential-process --certificate $(native "$CERT_DIR/client.pem") --private-key $(native "$CERT_DIR/client.key") --trust-anchor-arn $ta --profile-arn $pa --role-arn $ra
region = $region"
    mkdir -p "$(dirname "$AWS_CONFIG")"
    if [ -f "$AWS_CONFIG" ]; then
        cp -p "$AWS_CONFIG" "$AWS_CONFIG.bak-$(date +%Y%m%d-%H%M%S)"
    fi
    replace_profile_section "$AWS_CONFIG" "$PROFILE_NAME" "$block"
    info "Wrote [profile $PROFILE_NAME] to $AWS_CONFIG (backup alongside)"
    echo
    echo "Add to the ComfyUI .env so the nodes default to it:"
    echo "  AWS_BEDROCK_PROFILE=$PROFILE_NAME"
}

cmd_test() {
    info "Caller identity ($PROFILE_NAME)"
    aws sts get-caller-identity --profile "$PROFILE_NAME" --query Arn --output text
    local region
    region="${BEDROCK_REGION:-$(aws configure get region --profile "$PROFILE_NAME")}"
    info "Foundation models visible in $region"
    aws bedrock list-foundation-models --profile "$PROFILE_NAME" --region "$region" \
        --query "length(modelSummaries)" --output text
    info "Converse with $TEST_MODEL in $region"
    aws bedrock-runtime converse --profile "$PROFILE_NAME" --region "$region" \
        --model-id "$TEST_MODEL" \
        --messages '[{"role":"user","content":[{"text":"Reply with the single word: ok"}]}]' \
        --inference-config '{"maxTokens":16}' \
        --query "output.message.content[0].text" --output text
}

case "${1:-}" in
    certs)  cmd_certs ;;
    client) issue_client ;;
    body)   ca_body; echo ;;
    deploy) cmd_deploy ;;
    config) cmd_config ;;
    test)   cmd_test ;;
    all)    cmd_certs; cmd_deploy; cmd_config; cmd_test ;;
    *) sed -n '2,25p' "$0"; exit 1 ;;
esac
