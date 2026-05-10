#!/usr/bin/env bash
# test_lifecycle_45.sh - 라이프사이클 Step (4) Bedrock->Lambda, (5) Lambda->MCP decrypt_and_stage 검증
# 추가로 Phase 1D-5 (S3 평문 불가) 사전 체크 포함.
# Usage: ./scripts/test_lifecycle_45.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA="$ROOT/infra"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

ok()   { echo "  [PASS] $*"; }
fail() { echo "  [FAIL] $*"; exit 1; }
log()  { echo "[test] $*"; }

# ---- 0) Terraform output 로드 ---------------------------------------------
ENC_BUCKET=$(terraform -chdir="$INFRA" output -raw encrypted_code_bucket)
KB_BUCKET=$(terraform  -chdir="$INFRA" output -raw kb_staging_bucket)
LAMBDA_NAME=$(terraform -chdir="$INFRA" output -raw lambda_function_arn | awk -F: '{print $NF}')
PROJECT_ID="${PROJECT_ID:-default}"
SESSION_ID="test-$(date +%s)"

log "encrypted_code_bucket=$ENC_BUCKET"
log "kb_staging_bucket    =$KB_BUCKET"
log "lambda               =$LAMBDA_NAME"
log "session_id           =$SESSION_ID"

# ---- 1) Phase 1D-5: S3 .enc 가 ciphertext 인지 확인 -----------------------
log "[1D-5] Verifying encrypted_code bucket holds ciphertext only..."
FIRST_ENC=$(aws s3api list-objects-v2 --bucket "$ENC_BUCKET" \
    --prefix "encrypted_code/$PROJECT_ID/" \
    --query 'Contents[?ends_with(Key, `.enc`)].Key | [0]' --output text 2>/dev/null || echo "None")
if [ "$FIRST_ENC" = "None" ] || [ -z "$FIRST_ENC" ]; then
    fail "No .enc objects under encrypted_code/$PROJECT_ID/. Run encrypt_and_upload.sh first."
fi
aws s3 cp "s3://$ENC_BUCKET/$FIRST_ENC" "$TMP/sample.enc" --quiet
python3 - "$TMP/sample.enc" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
assert "sops" in data, "missing sops envelope -> looks like plaintext!"
assert data["sops"].get("kms"), "no KMS metadata"
print("ok:", sys.argv[1], "is SOPS ciphertext")
PY
ok "1D-5 ciphertext-only verified ($FIRST_ENC)"

# ---- 2) Step (4)+(5): Lambda 를 Bedrock Action Group 이벤트로 invoke -----
log "[Step 4+5] Invoking Lambda with synthetic Bedrock Action Group event..."
cat > "$TMP/event.json" <<EOF
{
  "messageVersion": "1.0",
  "agent": { "name": "agentbox-inspector", "id": "TEST", "alias": "TEST", "version": "1" },
  "actionGroup": "decrypt_and_stage",
  "function": "decrypt_and_stage",
  "sessionId": "$SESSION_ID",
  "parameters": [
    { "name": "project_id", "type": "string", "value": "$PROJECT_ID" }
  ]
}
EOF

# Windows Git Bash: cygpath converts POSIX temp path to Windows path for AWS CLI fileb://
if command -v cygpath &>/dev/null; then
    PAYLOAD_PATH="fileb://$(cygpath -w "$TMP/event.json")"
    RESP_PATH="$(cygpath -w "$TMP/lambda_resp.json")"
    META_PATH="$(cygpath -w "$TMP/invoke.meta")"
else
    PAYLOAD_PATH="fileb://$TMP/event.json"
    RESP_PATH="$TMP/lambda_resp.json"
    META_PATH="$TMP/invoke.meta"
fi

aws lambda invoke \
    --function-name "$LAMBDA_NAME" \
    --payload "$PAYLOAD_PATH" \
    --cli-binary-format raw-in-base64-out \
    "$RESP_PATH" >"$META_PATH"

STATUS=$(jq -r '.StatusCode // 0' "$META_PATH")
[ "$STATUS" = "200" ] || fail "Lambda invoke StatusCode=$STATUS  resp=$(cat "$RESP_PATH")"
ok "Lambda invoke 200"

# 함수 내부 에러 (FunctionError) 검사
FN_ERROR=$(jq -r '.FunctionError // ""' "$META_PATH")
[ -z "$FN_ERROR" ] || fail "Lambda FunctionError=$FN_ERROR  resp=$(cat "$RESP_PATH")"

# 응답 본문 파싱
BODY=$(jq -r '.response.functionResponse.responseBody.TEXT.body // empty' "$RESP_PATH")
[ -n "$BODY" ] || fail "Lambda response missing functionResponse.responseBody.TEXT.body : $(cat "$TMP/lambda_resp.json")"
echo "$BODY" | jq . >/dev/null 2>&1 || fail "responseBody.body is not JSON: $BODY"

KB_BKT=$(echo "$BODY" | jq -r '.kb_bucket // empty')
PREFIX=$(echo "$BODY" | jq -r '.prefix    // empty')
[ -n "$KB_BKT" ] && [ -n "$PREFIX" ] || fail "Lambda did not return kb_bucket/prefix : $BODY"
ok "Step 4 (Bedrock->Lambda) returned kb_bucket=$KB_BKT prefix=$PREFIX"

# ---- 3) Step (5) 결과 검증: KB 버킷에 평문이 staged 되어 있어야 함 -------
log "[Step 5] Verifying KB staging bucket has decrypted objects..."
sleep 2  # MCP 서버의 PutObject propagation
COUNT=$(aws s3 ls "s3://$KB_BKT/$PREFIX" --recursive | wc -l | tr -d ' ')
[ "$COUNT" -gt 0 ] || fail "KB bucket prefix $PREFIX has no staged objects"
ok "Step 5 (Lambda->MCP) staged $COUNT object(s) under s3://$KB_BKT/$PREFIX"

# (옵션) 첫 객체가 평문인지(=SOPS envelope 가 아닌지) 확인 - decrypt 가 실제로 일어났는지
FIRST_STAGE=$(aws s3 ls "s3://$KB_BKT/$PREFIX" --recursive | awk 'NR==1 {print $4}')
if [ -n "$FIRST_STAGE" ]; then
    aws s3 cp "s3://$KB_BKT/$FIRST_STAGE" "$TMP/staged.bin" --quiet
    if python3 -c "import json,sys;json.load(open(sys.argv[1]))['sops']" "$TMP/staged.bin" 2>/dev/null; then
        fail "Staged object is still SOPS-encrypted (decrypt did not run)"
    fi
    ok "Staged object is plaintext (KMS decrypt path verified)"
fi

# ---- 4) Cleanup: KB 버킷 비우기 (TTL/cleanup endpoint 동작 확인) ----------
log "[Cleanup] Deleting staged objects under $PREFIX ..."
aws s3 rm "s3://$KB_BKT/$PREFIX" --recursive --quiet
REMAIN=$(aws s3 ls "s3://$KB_BKT/$PREFIX" --recursive | wc -l | tr -d ' ') || true
[ "$REMAIN" = "0" ] || fail "KB bucket prefix not empty after cleanup ($REMAIN remain)"
ok "KB bucket cleanup verified"

echo ""
echo "================================================================"
echo "  ALL PASSED  -  Step (4) Bedrock->Lambda, (5) Lambda->MCP OK"
echo "================================================================"
