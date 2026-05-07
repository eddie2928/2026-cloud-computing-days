#!/usr/bin/env bash
# 1C-2: EC2 bootstrap - install AgentBox services
set -e

PROJECT="${project}"
REGION="${region}"
ADMIN_TOKEN="${admin_token}"

# Install Python 3.11
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip git sops

# Deploy application
mkdir -p /opt/agentbox
cd /opt/agentbox
python3.11 -m venv venv
source venv/bin/activate
pip install grpcio protobuf fastapi uvicorn boto3 pydantic loguru pyyaml sentence-transformers --quiet

# Write env config
cat > /opt/agentbox/.env << EOF
AWS_REGION=$REGION
PROJECT_NAME=$PROJECT
ADMIN_TOKEN=$ADMIN_TOKEN
GRPC_CERTS_DIR=/opt/agentbox/certs/grpc
EOF

# 1C-2: systemd service files
cat > /etc/systemd/system/agentbox-grpc.service << 'SVC'
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

cat > /etc/systemd/system/agentbox-mcp.service << 'SVC'
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

cat > /etc/systemd/system/agentbox-saas.service << 'SVC'
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

systemctl daemon-reload
systemctl enable agentbox-grpc agentbox-mcp agentbox-saas
systemctl start agentbox-grpc agentbox-mcp agentbox-saas
