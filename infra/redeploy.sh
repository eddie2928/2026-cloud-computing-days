#!/bin/bash
# Re-run deployment on a running EC2 instance.
# Usage (on the instance):  sudo bash ~/redeploy.sh [branch]
set -euo pipefail
exec > >(tee /var/log/redeploy.log) 2>&1

BRANCH="${1:-${GIT_BRANCH:-master}}"
APP_DIR=/opt/app

echo "==> Redeploy start (branch=$BRANCH)"

# 1. Stop API (nginx keeps serving the old frontend until rebuild completes)
systemctl stop qna-api || true

# 2. Pull latest code
cd "$APP_DIR"
sudo -u ec2-user git fetch --all --prune
sudo -u ec2-user git checkout "$BRANCH"
sudo -u ec2-user git reset --hard "origin/$BRANCH"

# 3. Backend deps
cd "$APP_DIR/backend"
# venv may be root-owned from first boot; chown so ec2-user can install new packages
chown -R ec2-user:ec2-user "$APP_DIR/backend/.venv"
sudo -u ec2-user .venv/bin/pip install --upgrade pip
sudo -u ec2-user .venv/bin/pip install -r requirements.txt

# 4. Frontend build
cd "$APP_DIR/frontend"
# Ensure ec2-user can overwrite dist/ (may have been created by root on first boot)
chown -R ec2-user:ec2-user "$APP_DIR/frontend/dist" 2>/dev/null || true
sudo -u ec2-user npm ci
sudo -u ec2-user npm run build
sudo -u ec2-user rm -rf node_modules

# 5. Alembic migration + seed
cd "$APP_DIR/backend"
set -a; source /etc/qna-diary/env; set +a
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_holidays

# 6. Restart services
systemctl daemon-reload
systemctl restart qna-api
systemctl reload nginx

# 7. CloudFront cache invalidation (so the new frontend appears immediately)
if [ -n "${CLOUDFRONT_DISTRIBUTION_ID:-}" ]; then
  echo "==> Invalidating CloudFront cache (distribution=$CLOUDFRONT_DISTRIBUTION_ID)"
  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text) \
    && echo "    invalidation id: $INVALIDATION_ID" \
    || echo "    WARN: invalidation failed (continuing)"
else
  echo "==> Skipping CloudFront invalidation (CLOUDFRONT_DISTRIBUTION_ID not set)"
fi

echo "==> Redeploy done"
systemctl --no-pager status qna-api | head -n 20

echo "==> Tailing qna-api logs (Ctrl+C to exit)"
journalctl -u qna-api -f
