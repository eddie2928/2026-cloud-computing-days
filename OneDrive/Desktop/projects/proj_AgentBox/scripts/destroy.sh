#!/usr/bin/env bash
# destroy.sh — Destroy infra while preserving the CMK in AWS
# Usage: ./scripts/destroy.sh [extra terraform destroy flags]
#
# Strategy: remove KMS resources from Terraform state before destroy.
# The physical AWS key is untouched; only state tracking is removed.
set -euo pipefail
: "${DRY_RUN:=0}"

INFRA_DIR="$(cd "$(dirname "$0")/../infra" && pwd)"
cd "$INFRA_DIR"

echo "==> Removing KMS resources from Terraform state (preserving physical AWS key)"
# Addresses use [0] suffix because these resources have count = 1 on first deploy.
# If they were never in state (re-apply with existing key), these are no-ops.
terraform state rm 'aws_kms_key.sops[0]'   2>/dev/null && echo "    Removed aws_kms_key.sops[0]"   || echo "    aws_kms_key.sops[0] not in state (skipping)"
terraform state rm 'aws_kms_alias.sops[0]' 2>/dev/null && echo "    Removed aws_kms_alias.sops[0]" || echo "    aws_kms_alias.sops[0] not in state (skipping)"

echo ""
echo "==> Pre-destroy: Lambda function cleanup (unblock VPC ENI)"
# Lambda VPC Hyperplane ENI는 함수 삭제 후 10~20분간 in-use 상태 유지.
# terraform destroy 전에 미리 삭제해 ENI 정리 시간을 최대한 확보한다.
LAMBDA_ARN=$(terraform output -raw lambda_function_arn 2>/dev/null || true)
if [[ -n "$LAMBDA_ARN" && "$LAMBDA_ARN" != *"No outputs"* ]]; then
    LAMBDA_NAME="${LAMBDA_ARN##*:}"
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "    [DRY_RUN] aws lambda delete-function --function-name ${LAMBDA_NAME} (skipped)"
    else
        echo "    Deleting Lambda function ${LAMBDA_NAME} …"
        aws lambda delete-function --function-name "$LAMBDA_NAME" 2>/dev/null \
            && echo "    Lambda deletion initiated" \
            || echo "    Lambda not found or already deleted (skipping)"
    fi
else
    echo "    No lambda_function_arn output found (skipping)"
fi

echo ""
echo "==> Pre-destroy: Bedrock Agent cleanup (skip-resource-in-use-check)"
# Terraform cannot delete an ENABLED action group; pre-delete the agent to avoid
# the deadlock: bedrockagent blocks lambda -> lambda blocks mcp-EC2 -> mcp-EC2
# blocks IGW detachment (AWS forbids IGW detach while public-IP instances exist).
AGENT_ID=$(terraform output -raw bedrock_agent_id 2>/dev/null || true)
if [[ -n "$AGENT_ID" && "$AGENT_ID" != *"No outputs"* ]]; then
    echo "    Deleting Bedrock agent ${AGENT_ID} …"
    aws bedrock-agent delete-agent --agent-id "$AGENT_ID" \
        --skip-resource-in-use-check 2>/dev/null \
        && echo "    Agent deletion initiated" \
        || echo "    Agent not found or already deleted (skipping)"
else
    echo "    No bedrock_agent_id output found (skipping)"
fi

echo ""
echo "==> terraform destroy"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [DRY_RUN] terraform destroy 생략 → plan -destroy 로 대체"
    terraform plan -destroy -refresh=false
else
    terraform destroy "$@"
fi
