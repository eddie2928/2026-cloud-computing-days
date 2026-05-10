#!/usr/bin/env bash
# deploy.sh — Full deployment: init -> plan -> apply -> health check
# Usage: ./scripts/deploy.sh [-auto-approve] [extra terraform apply flags]
set -euo pipefail
: "${DRY_RUN:=0}"

INFRA_DIR="$(cd "$(dirname "$0")/../infra" && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${TF_VAR_project:-agentbox}"
ALIAS_NAME="alias/${PROJECT}-sops-key"

echo "==> [1/11] Checking for existing KMS key: ${ALIAS_NAME}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [DRY_RUN] Skipping KMS describe-key lookup"
    export TF_VAR_existing_kms_key_arn=""
else
    EXISTING_ARN=$(aws kms describe-key \
        --key-id "$ALIAS_NAME" \
        --query 'KeyMetadata.Arn' \
        --output text 2>/dev/null || true)

    if [[ -n "$EXISTING_ARN" && "$EXISTING_ARN" != "None" ]]; then
        echo "    Found existing CMK: ${EXISTING_ARN}"
        KEY_STATE=$(aws kms describe-key --key-id "$EXISTING_ARN" \
            --query 'KeyMetadata.KeyState' --output text 2>/dev/null || echo "Unknown")
        if [[ "$KEY_STATE" != "Enabled" ]]; then
            echo "ERROR: KMS key state is '${KEY_STATE}', not 'Enabled'. Aborting."
            echo "       Run: aws kms enable-key --key-id ${EXISTING_ARN}"
            exit 1
        fi
        export TF_VAR_existing_kms_key_arn="$EXISTING_ARN"
    else
        echo "    No existing CMK found — a new key will be created."
        export TF_VAR_existing_kms_key_arn=""
    fi
fi

cd "$INFRA_DIR"

echo ""
echo "==> [2/11] terraform init"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [DRY_RUN] terraform init -upgrade=false"
    terraform init -upgrade=false -backend=false 2>/dev/null || terraform init -upgrade=false
else
    terraform init -upgrade=false
fi

echo ""
echo "==> [3/11] terraform apply"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [DRY_RUN] terraform apply 생략 → plan 으로 대체"
    terraform plan -refresh=false -var-file="${TFVARS:-../terraform.tfvars}" 2>/dev/null || \
        terraform plan -refresh=false
    echo "[DRY_RUN] deploy.sh 완료 (plan only)"
    exit 0
else
    terraform apply "$@"
fi

echo ""
echo "==> [4/11] Extracting terraform outputs"
APP_PUBLIC_IP=$(terraform output -raw app_public_ip 2>/dev/null || echo "")
MCP_PUBLIC_IP=$(terraform output -raw mcp_public_ip 2>/dev/null || echo "")
MCP_PRIVATE_IP=$(terraform output -raw mcp_private_ip 2>/dev/null || echo "")
APP_INSTANCE_ID=$(terraform output -raw app_instance_id 2>/dev/null || echo "")
MCP_INSTANCE_ID=$(terraform output -raw mcp_instance_id 2>/dev/null || echo "")
KMS_KEY_ARN=$(terraform output -raw kms_key_arn 2>/dev/null || echo "")

echo "    app_public_ip   = ${APP_PUBLIC_IP}"
echo "    mcp_public_ip   = ${MCP_PUBLIC_IP}"
echo "    mcp_private_ip  = ${MCP_PRIVATE_IP}"
echo "    app_instance_id = ${APP_INSTANCE_ID}"
echo "    mcp_instance_id = ${MCP_INSTANCE_ID}"

echo ""
echo "==> [5/11] Updating .sops.yaml and generating mTLS certs"
cd "$(dirname "$INFRA_DIR")"
if [[ -n "$KMS_KEY_ARN" ]]; then
    cat > .sops.yaml <<SOPSEOF
creation_rules:
  - kms: ${KMS_KEY_ARN}
SOPSEOF
    echo "    .sops.yaml updated with KMS key: ${KMS_KEY_ARN}"
fi

if [[ ! -f "certs/grpc/agentbox-ca.crt" ]]; then
    bash "${SCRIPTS_DIR}/gen_mtls_certs.sh" certs/grpc
else
    echo "    certs/grpc already present, skipping gen"
fi

echo ""
echo "==> [6/11] Writing .env.endpoint"
cat > .env.endpoint <<ENVEOF
EC2_GRPC_HOST=${APP_PUBLIC_IP}
EC2_GRPC_PORT=50051
ENVEOF
echo "    .env.endpoint written"

echo ""
echo "==> [7/11] Waiting for SSM registration (timeout 3 min)"
for i in $(seq 1 18); do
    APP_STATUS=$(aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=${APP_INSTANCE_ID}" \
        --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || echo "Unknown")
    MCP_STATUS=$(aws ssm describe-instance-information \
        --filters "Key=InstanceIds,Values=${MCP_INSTANCE_ID}" \
        --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || echo "Unknown")

    echo "    [${i}/18] app=${APP_STATUS}, mcp=${MCP_STATUS}"

    if [[ "$APP_STATUS" == "Online" && "$MCP_STATUS" == "Online" ]]; then
        echo "    Both instances Online"
        break
    fi

    if [[ $i -eq 18 ]]; then
        echo "ERROR: SSM registration timeout after 3 minutes."
        echo "       Check: aws ssm describe-instance-information"
        exit 1
    fi
    sleep 10
done

echo ""
echo "==> [8/11] Pushing certs/CA via SSM"
CA_CONTENT=$(base64 -w0 certs/grpc/agentbox-ca.crt 2>/dev/null || base64 certs/grpc/agentbox-ca.crt)
EC2_CRT=$(base64 -w0 certs/grpc/ec2.crt 2>/dev/null || base64 certs/grpc/ec2.crt)
EC2_KEY=$(base64 -w0 certs/grpc/ec2.key 2>/dev/null || base64 certs/grpc/ec2.key)

SSM_CMD=$(aws ssm send-command \
    --instance-ids "$APP_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[
        'mkdir -p /opt/agentbox/certs/grpc',
        'echo ${CA_CONTENT} | base64 -d > /opt/agentbox/certs/grpc/agentbox-ca.crt',
        'echo ${EC2_CRT}    | base64 -d > /opt/agentbox/certs/grpc/ec2.crt',
        'echo ${EC2_KEY}    | base64 -d > /opt/agentbox/certs/grpc/ec2.key',
        'chmod 600 /opt/agentbox/certs/grpc/ec2.key',
        'systemctl restart agentbox-grpc'
    ]" \
    --query 'Command.CommandId' --output text 2>/dev/null || echo "")

if [[ -n "$SSM_CMD" ]]; then
    sleep 5
    echo "    Cert push SSM command: ${SSM_CMD}"
fi

echo ""
echo "==> [9/11] Checking systemd service status via SSM"
for INSTANCE_ID in "$APP_INSTANCE_ID" "$MCP_INSTANCE_ID"; do
    if [[ "$INSTANCE_ID" == "$APP_INSTANCE_ID" ]]; then
        SERVICES="agentbox-grpc agentbox-saas"
        LABEL="app"
    else
        SERVICES="agentbox-mcp"
        LABEL="mcp"
    fi

    CMD_ID=$(aws ssm send-command \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=['systemctl is-active ${SERVICES}']" \
        --query 'Command.CommandId' --output text 2>/dev/null || echo "")

    if [[ -n "$CMD_ID" ]]; then
        sleep 5
        STATUS=$(aws ssm get-command-invocation \
            --command-id "$CMD_ID" --instance-id "$INSTANCE_ID" \
            --query 'StandardOutputContent' --output text 2>/dev/null || echo "unknown")
        echo "    ${LABEL} services: ${STATUS}"
        if echo "$STATUS" | grep -q "inactive\|failed"; then
            echo "    Fetching journal for ${LABEL}..."
            aws ssm send-command \
                --instance-ids "$INSTANCE_ID" \
                --document-name "AWS-RunShellScript" \
                --parameters "commands=['journalctl -u ${SERVICES// / -u } --no-pager -n 30']" \
                --output text 2>/dev/null || true
        fi
    fi
done

echo ""
echo "==> [10/11] Health check: MCP /healthz and app gRPC port"
MCP_HEALTH_CMD=$(aws ssm send-command \
    --instance-ids "$MCP_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=['curl -sf http://localhost:8080/healthz && echo OK || echo FAIL']" \
    --query 'Command.CommandId' --output text 2>/dev/null || echo "")

APP_PORT_CMD=$(aws ssm send-command \
    --instance-ids "$APP_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=['ss -tlnp | grep :50051 && echo GRPC_OK || echo GRPC_FAIL']" \
    --query 'Command.CommandId' --output text 2>/dev/null || echo "")

if [[ -n "$MCP_HEALTH_CMD" || -n "$APP_PORT_CMD" ]]; then
    sleep 8
    for CMD_ID in "$MCP_HEALTH_CMD" "$APP_PORT_CMD"; do
        [[ -z "$CMD_ID" ]] && continue
        OUT=$(aws ssm get-command-invocation \
            --command-id "$CMD_ID" --instance-id \
            "$([ "$CMD_ID" == "$MCP_HEALTH_CMD" ] && echo "$MCP_INSTANCE_ID" || echo "$APP_INSTANCE_ID")" \
            --query 'StandardOutputContent' --output text 2>/dev/null || echo "")
        echo "    $OUT"
    done
fi

echo ""
echo "==> [11/11] Deployment OK"
SAAS_URL=$(terraform output -raw saas_url 2>/dev/null || echo "http://${APP_PUBLIC_IP}:8000")
echo "    SaaS URL: ${SAAS_URL}"
echo "    App IP:   ${APP_PUBLIC_IP}"
echo "    MCP IP:   ${MCP_PUBLIC_IP} (private: ${MCP_PRIVATE_IP})"
echo ""
echo "Deployment complete!"
