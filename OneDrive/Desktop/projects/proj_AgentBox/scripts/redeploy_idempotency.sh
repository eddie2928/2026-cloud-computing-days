#!/usr/bin/env bash
# redeploy_idempotency.sh — destroy → deploy → health check 자동화
#
# 멱등성 보장: 임의의 인프라 상태에서 본 스크립트를 실행하면
# 항상 동일한 "깨끗한 동작 상태" 로 수렴한다.
#
# Usage:
#   bash scripts/redeploy_idempotency.sh                 # 실제 실행 (확인 prompt)
#   bash scripts/redeploy_idempotency.sh -y              # 자동 승인
#   DRY_RUN=1 bash scripts/redeploy_idempotency.sh       # plan 만 출력 (안전)
#
# 환경변수:
#   DRY_RUN=1                : destroy/deploy 가 plan 만 실행
#   ADMIN_TOKEN=<token>      : health check 의 /api/audit 검증에 사용
#   SKIP_DASHBOARD_DEPLOY=1  : deploy_static.sh 단계 건너뜀

set -euo pipefail
: "${DRY_RUN:=0}"
: "${SKIP_DASHBOARD_DEPLOY:=0}"

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PROJ_ROOT/scripts"
AUTO_APPROVE="${1:-}"

log() { echo "[$(date +%H:%M:%S)] $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

# ── 0. 사전 점검 ─────────────────────────────────────────────────────────────
log "[0/5] 사전 점검"
command -v aws       >/dev/null || fail "aws CLI 가 PATH 에 없음"
command -v terraform >/dev/null || fail "terraform 이 PATH 에 없음"
if [[ "$DRY_RUN" == "1" ]]; then
    log "    DRY_RUN=1 — destroy/deploy 는 plan 만 실행됨 (AWS 자격증명 체크 건너뜀)"
else
    aws sts get-caller-identity --region us-east-1 >/dev/null \
        || fail "AWS 자격증명이 유효하지 않음"
fi

# ── 1. destroy.sh ───────────────────────────────────────────────────────────
log "[1/5] destroy.sh (KMS 보존)"
if [[ "$DRY_RUN" == "1" ]]; then
    DRY_RUN=1 bash "$SCRIPTS_DIR/destroy.sh"
else
    if [[ "$AUTO_APPROVE" == "-y" ]]; then
        bash "$SCRIPTS_DIR/destroy.sh" -auto-approve
    else
        bash "$SCRIPTS_DIR/destroy.sh"
    fi
fi

# ── 2. deploy.sh ────────────────────────────────────────────────────────────
log "[2/5] deploy.sh"
if [[ "$DRY_RUN" == "1" ]]; then
    DRY_RUN=1 bash "$SCRIPTS_DIR/deploy.sh"
else
    if [[ "$AUTO_APPROVE" == "-y" ]]; then
        bash "$SCRIPTS_DIR/deploy.sh" -auto-approve
    else
        bash "$SCRIPTS_DIR/deploy.sh"
    fi
fi

if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN 종료 — 실제 deploy 가 아니므로 health check 건너뜀"
    exit 0
fi

# ── 3. terraform output 으로 SaaS URL 획득 ─────────────────────────────────
log "[3/5] terraform output 확인"
cd "$PROJ_ROOT/infra"
APP_IP=$(terraform output -raw app_public_ip 2>/dev/null) \
    || fail "app_public_ip 출력 없음"
SAAS_URL="http://${APP_IP}:8000"
log "    SaaS URL = $SAAS_URL"
cd "$PROJ_ROOT"

# ── 4. dashboard 배포 (옵션) ───────────────────────────────────────────────
if [[ "$SKIP_DASHBOARD_DEPLOY" != "1" ]]; then
    log "[4/5] dashboard 빌드 + deploy_static.sh"
    [[ -d dashboard/node_modules ]] || (cd dashboard && npm ci)
    (cd dashboard && npm run build)
    rm -rf ec2/saas/static
    mkdir -p ec2/saas/static
    cp -r dashboard/dist/* ec2/saas/static/
    bash "$SCRIPTS_DIR/deploy_static.sh"
else
    log "[4/5] SKIP_DASHBOARD_DEPLOY=1 — dashboard 배포 건너뜀"
fi

# ── 5. Health Check 5종 ────────────────────────────────────────────────────
log "[5/5] Health Check"
sleep 5

# 5-a. /healthz
CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/healthz")
[[ "$CODE" == "200" ]] || fail "5-a /healthz expected 200, got $CODE"
log "    5-a /healthz 200 OK"

# 5-b. /audit (HTML 무토큰)
CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/audit")
[[ "$CODE" == "200" ]] || fail "5-b /audit expected 200, got $CODE"
log "    5-b /audit HTML 200 OK"

# 5-c. /api/audit 무토큰 401
CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SAAS_URL}/api/audit")
[[ "$CODE" == "401" ]] || fail "5-c /api/audit (no token) expected 401, got $CODE"
log "    5-c /api/audit 401 (no token) OK"

# 5-d. /api/audit 토큰 200 (선택 — ADMIN_TOKEN 있을 때만)
if [[ -n "${ADMIN_TOKEN:-}" ]]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-Admin-Token: $ADMIN_TOKEN" "${SAAS_URL}/api/audit?limit=1")
    [[ "$CODE" == "200" ]] || fail "5-d /api/audit (with token) expected 200, got $CODE"
    log "    5-d /api/audit 200 (with token) OK"
else
    log "    5-d /api/audit (token check skipped — ADMIN_TOKEN not set)"
fi

# 5-e. /api/pipeline/stream WebSocket 핸드셰이크 (python 1-liner)
python3 -c "
import sys
from urllib.parse import urlparse
try:
    from websockets.sync.client import connect
except ImportError:
    print('websockets 미설치 — skip', file=sys.stderr); sys.exit(0)
url = '${SAAS_URL}'.replace('http://', 'ws://') + '/api/pipeline/stream'
with connect(url, open_timeout=5) as ws:
    pass
" && log "    5-e WebSocket /api/pipeline/stream 핸드셰이크 OK" \
  || fail "5-e WebSocket 핸드셰이크 실패"

log "✓ redeploy_idempotency.sh 완료 — 모든 헬스체크 통과"
log "  SaaS URL: $SAAS_URL"
