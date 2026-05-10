#!/usr/bin/env bash
# MCP-EC2 bootstrap: sops + MCP service (no Bedrock/DynamoDB)
set -eux
exec > /var/log/agentbox-userdata.log 2>&1

PROJECT="${project}"
REGION="${region}"
ADMIN_TOKEN="${admin_token}"
CODE_S3_URI="${code_s3_uri}"

apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip git unzip awscli amazon-cloudwatch-agent

# sops via GitHub release binary (apt package unreliable)
curl -fsSL https://github.com/getsops/sops/releases/download/v3.12.2/sops-v3.12.2.linux.amd64 \
    -o /usr/local/bin/sops
chmod +x /usr/local/bin/sops

mkdir -p /opt/agentbox/logs
aws s3 cp "$CODE_S3_URI" /tmp/code.zip --region "$REGION"
unzip -q -o /tmp/code.zip -d /opt/agentbox
chown -R ubuntu:ubuntu /opt/agentbox

cd /opt/agentbox
python3.11 -m venv venv
source venv/bin/activate
pip install --quiet boto3 fastapi uvicorn pydantic loguru

cat > /opt/agentbox/.env <<ENVEOF
AWS_REGION=$REGION
PROJECT_NAME=$PROJECT
ADMIN_TOKEN=$ADMIN_TOKEN
MCP_PORT=8080
ENVEOF

cat > /etc/systemd/system/agentbox-mcp.service <<'SVC'
[Unit]
Description=AgentBox MCP Server (decrypt_and_stage)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/agentbox
EnvironmentFile=/opt/agentbox/.env
ExecStart=/opt/agentbox/venv/bin/python -m ec2.mcp_server.server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

amazon-cloudwatch-agent-ctl -a fetch-config \
    -m ec2 -c ssm:/agentbox/cloudwatch-agent-config -s

systemctl daemon-reload
systemctl enable agentbox-mcp
systemctl start  agentbox-mcp
