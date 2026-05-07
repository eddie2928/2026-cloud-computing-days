#!/usr/bin/env bash
# 1A-1: Ubuntu 22.04 VM bootstrap (Multipass)
# Run on Windows/macOS host to create a Multipass VM for AgentBox transparent proxy.
# Completion check: uname -r >= 5.15 AND bpftool feature

set -e

VM_NAME="${AGENTBOX_VM:-agentbox-dev}"
CPUS=2
MEM=4G
DISK=20G

echo "[agentbox] Creating Multipass VM: $VM_NAME (Ubuntu 22.04)"
multipass launch 22.04 --name "$VM_NAME" --cpus "$CPUS" --memory "$MEM" --disk "$DISK"

echo "[agentbox] Verifying kernel version >= 5.15 ..."
multipass exec "$VM_NAME" -- uname -r

echo "[agentbox] Running initial apt update ..."
multipass exec "$VM_NAME" -- sudo apt-get update -qq

echo "[agentbox] Mounting project directory into VM ..."
PROJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
multipass mount "$PROJ_DIR" "$VM_NAME":/agentbox

echo ""
echo "  VM ready: $VM_NAME"
echo "  Shell in: multipass shell $VM_NAME"
echo "  Next    : sudo bash /agentbox/scripts/install_ebpf.sh"
