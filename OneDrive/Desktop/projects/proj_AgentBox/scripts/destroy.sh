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
echo "==> terraform destroy"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "    [DRY_RUN] terraform destroy 생략 → plan -destroy 로 대체"
    terraform plan -destroy -refresh=false
else
    terraform destroy "$@"
fi
