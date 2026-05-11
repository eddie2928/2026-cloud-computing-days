#!/usr/bin/env bash
# Update admin_cidr / endpoint_cidr in terraform.tfvars to current public IP,
# then run terraform apply (targeting only the security groups).
#
# Usage:
#   bash scripts/update_my_ip.sh          # prompt before apply
#   bash scripts/update_my_ip.sh -y       # auto-approve

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TFVARS="$PROJ_ROOT/infra/terraform.tfvars"
AUTO_APPROVE="${1:-}"

# ── 1. Detect current public IP ────────────────────────────────────────────────
echo "[1/3] Detecting public IP..."
MY_IP=$(curl -fsSL https://api.ipify.org)
MY_CIDR="${MY_IP}/32"
echo "      Current IP: $MY_CIDR"

# ── 2. Update terraform.tfvars ─────────────────────────────────────────────────
echo "[2/3] Updating $TFVARS ..."
sed -i "s|endpoint_cidr = \".*\"|endpoint_cidr = \"$MY_CIDR\"|" "$TFVARS"
sed -i "s|admin_cidr    = \".*\"|admin_cidr    = \"$MY_CIDR\"|" "$TFVARS"
echo "      Done. endpoint_cidr = admin_cidr = $MY_CIDR"

# ── 3. terraform apply (SG targets only) ───────────────────────────────────────
echo "[3/3] Running terraform apply (security groups only)..."
echo "      ⚠ OneDrive sync 일시중지 권장 (tfstate lock 방지)"

cd "$PROJ_ROOT/infra"

if [ "$AUTO_APPROVE" = "-y" ]; then
    terraform apply \
      -target=aws_security_group.app \
      -target=aws_security_group.mcp \
      -auto-approve
else
    terraform apply \
      -target=aws_security_group.app \
      -target=aws_security_group.mcp
fi

echo ""
echo "✓ Security group updated to $MY_CIDR"
echo "  http://54.165.51.239:8000/ 에서 대시보드를 확인하세요."
