#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CA_CRT="$SCRIPT_DIR/../certs/agentbox-ca.crt"

if [ ! -f "$CA_CRT" ]; then
    echo "ERROR: $CA_CRT not found. Run 'agentbox ca install' first."
    exit 1
fi

sudo cp "$CA_CRT" /usr/local/share/ca-certificates/agentbox-ca.crt
sudo update-ca-certificates
echo "AgentBox CA installed into system trust store."
