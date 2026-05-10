#!/usr/bin/env bash
# App-EC2 bootstrap: gRPC + SaaS services (no sops/KMS)
set -eux
exec > /var/log/agentbox-userdata.log 2>&1

PROJECT="${project}"
REGION="${region}"
ADMIN_TOKEN="${admin_token}"
CODE_S3_URI="${code_s3_uri}"
BEDROCK_AGENT_ID="${bedrock_agent_id}"
BEDROCK_AGENT_ALIAS_ID="${bedrock_agent_alias_id}"
MCP_PRIVATE_IP="${mcp_private_ip}"

apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip git unzip awscli amazon-cloudwatch-agent

mkdir -p /opt/agentbox/logs
aws s3 cp "$CODE_S3_URI" /tmp/code.zip --region "$REGION"
unzip -q -o /tmp/code.zip -d /opt/agentbox
chown -R ubuntu:ubuntu /opt/agentbox

cd /opt/agentbox
python3.11 -m venv venv
source venv/bin/activate
pip install --quiet \
    grpcio protobuf fastapi uvicorn boto3 pydantic loguru pyyaml \
    sentence-transformers numpy requests

cat > /opt/agentbox/.env <<ENVEOF
AWS_REGION=$REGION
PROJECT_NAME=$PROJECT
ADMIN_TOKEN=$ADMIN_TOKEN
GRPC_CERTS_DIR=/opt/agentbox/certs/grpc
BEDROCK_AGENT_ID=$BEDROCK_AGENT_ID
BEDROCK_AGENT_ALIAS_ID=$BEDROCK_AGENT_ALIAS_ID
MCP_SERVER_URL=http://$MCP_PRIVATE_IP:8080
ENVEOF

cat > /etc/systemd/system/agentbox-grpc.service <<'SVC'
[Unit]
Description=AgentBox gRPC Inspector Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/agentbox
EnvironmentFile=/opt/agentbox/.env
ExecStart=/opt/agentbox/venv/bin/python -m ec2.grpc_server.server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVC

cat > /etc/systemd/system/agentbox-saas.service <<'SVC'
[Unit]
Description=AgentBox SaaS Dashboard
After=network.target agentbox-grpc.service

[Service]
User=ubuntu
WorkingDirectory=/opt/agentbox
EnvironmentFile=/opt/agentbox/.env
ExecStart=/opt/agentbox/venv/bin/python -m ec2.saas.server
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
systemctl enable agentbox-grpc agentbox-saas
systemctl start  agentbox-grpc agentbox-saas
