#!/usr/bin/env bash
# One-shot script: build dashboard, upload to S3, deploy to EC2 via SSM.
set -euo pipefail

PROJ="/mnt/c/Users/ab550/OneDrive/Desktop/projects/proj_AgentBox"
BUCKET="agentbox-encrypted-code"
INSTANCE="i-001503fc70640603d"
REGION="us-east-1"
S3_KEY="_dist/saas_update.tar.gz"

echo "[1/4] Creating archive..."
tar -czf /tmp/saas_update.tar.gz \
  -C "$PROJ" \
  ec2/saas/server.py \
  ec2/saas/static

echo "[2/4] Uploading to s3://$BUCKET/$S3_KEY (AES256, no KMS) ..."
# Upload with AES256 so EC2 app-role (no kms:Decrypt) can download it
aws s3 cp /tmp/saas_update.tar.gz "s3://$BUCKET/$S3_KEY" \
  --sse AES256 --region "$REGION"

echo "[3/4] Building SSM params (direct S3 download, base64-encoded command)..."
python3 - "$BUCKET" "$S3_KEY" "$REGION" "$INSTANCE" <<'PYEOF'
import json, base64, sys

bucket, key, region, instance = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

inner = f"""#!/bin/bash
set -euo pipefail
aws s3 cp s3://{bucket}/{key} /tmp/saas_update.tar.gz --region {region}
tar -xzf /tmp/saas_update.tar.gz -C /opt/agentbox
systemctl restart agentbox-saas
echo DONE
systemctl is-active agentbox-saas
"""
encoded = base64.b64encode(inner.encode()).decode()
wrapper = f"echo {encoded} | base64 -d | bash"

payload = {
    "DocumentName": "AWS-RunShellScript",
    "InstanceIds": [instance],
    "Parameters": {"commands": [wrapper]},
}
with open("/tmp/ssm_input.json", "w") as f:
    json.dump(payload, f)
print("SSM JSON written OK")
PYEOF

echo "[4/4] Sending SSM command to EC2..."
COMMAND_ID=$(aws ssm send-command \
  --cli-input-json file:///tmp/ssm_input.json \
  --region "$REGION" \
  --query "Command.CommandId" \
  --output text)

echo "SSM CommandId: $COMMAND_ID"
echo "Waiting 15s for command to complete..."
sleep 15

aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE" \
  --region "$REGION" \
  --query "{Status:Status,Output:StandardOutputContent,Error:StandardErrorContent}" \
  --output json
