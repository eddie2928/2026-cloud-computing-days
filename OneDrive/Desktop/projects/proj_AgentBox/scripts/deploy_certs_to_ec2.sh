#!/usr/bin/env bash
# Deploy local mTLS certs to EC2 and restart agentbox-grpc service.
# Usage: bash scripts/deploy_certs_to_ec2.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/../infra"

echo "[cert-deploy] terraform output에서 app instance ID / IP 조회 중..."
INSTANCE_ID=$(cd "$INFRA_DIR" && terraform output -raw app_instance_id 2>/dev/null) \
  || { echo "ERROR: terraform output 조회 실패. 'cd infra && terraform init' 후 재시도하세요."; exit 1; }
APP_IP=$(cd "$INFRA_DIR" && terraform output -raw app_public_ip 2>/dev/null) \
  || { echo "ERROR: app_public_ip 조회 실패."; exit 1; }
[[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "null" ]] && \
  { echo "ERROR: app_instance_id가 비어 있습니다. terraform apply가 완료됐는지 확인하세요."; exit 1; }
[[ -z "$APP_IP" || "$APP_IP" == "null" ]] && \
  { echo "ERROR: app_public_ip가 비어 있습니다."; exit 1; }
echo "[cert-deploy] 대상 인스턴스: $INSTANCE_ID ($APP_IP)"

CERT_SRC="$HOME/.agentbox/certs/grpc"
CERT_DST="/opt/agentbox/certs/grpc"

echo "[cert-deploy] 로컬 cert 확인..."
for f in agentbox-ca.crt ec2.crt ec2.key; do
    [[ -f "$CERT_SRC/$f" ]] || { echo "ERROR: $CERT_SRC/$f 없음"; exit 1; }
done
echo "[cert-deploy] 로컬 cert (필수 3개) OK"

echo "[cert-deploy] base64 인코딩..."
CA_CRT=$(base64 -w0 "$CERT_SRC/agentbox-ca.crt")
EC2_CRT=$(base64 -w0 "$CERT_SRC/ec2.crt")
EC2_KEY=$(base64 -w0 "$CERT_SRC/ec2.key")

# endpoint.crt is optional — deploy only if present
EP_CRT_CMD=""
if [[ -f "$CERT_SRC/endpoint.crt" ]]; then
    EP_CRT=$(base64 -w0 "$CERT_SRC/endpoint.crt")
    EP_CRT_CMD="\"echo ${EP_CRT} | base64 -d > ${CERT_DST}/endpoint.crt\","
fi

echo "[cert-deploy] EC2에 cert 업로드 중..."
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[
    \"echo ${CA_CRT}  | base64 -d > ${CERT_DST}/agentbox-ca.crt\",
    \"echo ${EC2_CRT} | base64 -d > ${CERT_DST}/ec2.crt\",
    \"echo ${EC2_KEY} | base64 -d > ${CERT_DST}/ec2.key\",
    ${EP_CRT_CMD}
    \"chmod 600 ${CERT_DST}/*.key\",
    \"chown ubuntu:ubuntu ${CERT_DST}/*.crt ${CERT_DST}/*.key\",
    \"systemctl restart agentbox-grpc\",
    \"sleep 2\",
    \"systemctl is-active agentbox-grpc && echo CERT_DEPLOY_OK || echo CERT_DEPLOY_FAIL\"
  ]" \
  --output text --query 'Command.CommandId')

echo "[cert-deploy] CMD_ID: $CMD_ID"
echo "[cert-deploy] 완료 대기 중 (15초)..."
sleep 15

RESULT=$(aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --output json)

STATUS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['Status'])")
OUTPUT=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('StandardOutputContent',''))")
ERRORS=$(echo "$RESULT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('StandardErrorContent','')[:300])")

echo ""
echo "===== SSM 실행 결과 ====="
echo "Status : $STATUS"
echo "Output : $OUTPUT"
[[ -n "$ERRORS" ]] && echo "Errors : $ERRORS"

if echo "$OUTPUT" | grep -q "CERT_DEPLOY_OK"; then
    echo ""
    echo "[cert-deploy] ✓ EC2 cert 배포 완료. agentbox-grpc 서비스 정상 실행 중."

    # ~/.agentbox/env 의 GRPC_HOST 업데이트
    ENV_FILE="$HOME/.agentbox/env"
    if grep -q "^GRPC_HOST=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^GRPC_HOST=.*|GRPC_HOST=${APP_IP}|" "$ENV_FILE"
    else
        echo "GRPC_HOST=${APP_IP}" >> "$ENV_FILE"
    fi
    echo "[cert-deploy] ~/.agentbox/env GRPC_HOST → ${APP_IP}"

    # ~/.agentbox/endpoint 의 EC2_GRPC_HOST 업데이트 (agentbox init 이 읽음)
    ENDPOINT_FILE="$HOME/.agentbox/endpoint"
    if grep -q "^EC2_GRPC_HOST=" "$ENDPOINT_FILE" 2>/dev/null; then
        sed -i "s|^EC2_GRPC_HOST=.*|EC2_GRPC_HOST=${APP_IP}|" "$ENDPOINT_FILE"
    else
        printf "EC2_GRPC_HOST=%s\nEC2_GRPC_PORT=50051\n" "${APP_IP}" >> "$ENDPOINT_FILE"
    fi
    echo "[cert-deploy] ~/.agentbox/endpoint EC2_GRPC_HOST → ${APP_IP}"

    echo "[cert-deploy] 이제 'agentbox set -y' 를 다시 실행하세요."
else
    echo ""
    echo "[cert-deploy] ✗ 배포 실패 또는 서비스 미시작. Errors 확인 필요."
    exit 1
fi
