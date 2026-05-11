#!/usr/bin/env bash
set -euo pipefail
INSTANCE="i-001503fc70640603d"
REGION="us-east-1"

python3 - <<'PYEOF'
import json, base64

inner = """#!/bin/bash
ss -tlnp | grep 8000 || echo 'PORT 8000 NOT LISTENING'
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/ | head -c 200
"""
encoded = base64.b64encode(inner.encode()).decode()
payload = {
    "DocumentName": "AWS-RunShellScript",
    "InstanceIds": ["i-001503fc70640603d"],
    "Parameters": {"commands": [f"echo {encoded} | base64 -d | bash"]},
}
with open("/tmp/ssm_check.json", "w") as f:
    json.dump(payload, f)
print("JSON written")
PYEOF

CID=$(aws ssm send-command --cli-input-json file:///tmp/ssm_check.json --region "$REGION" --query "Command.CommandId" --output text)
echo "CommandId: $CID"
sleep 12
aws ssm get-command-invocation \
  --command-id "$CID" \
  --instance-id "$INSTANCE" \
  --region "$REGION" \
  --query "{Status:Status,Output:StandardOutputContent,Error:StandardErrorContent}" \
  --output json
