#!/usr/bin/env bash
# Source this file to activate AgentBox proxy for Claude Code.
# Usage:
#   source ~/agentbox/scripts/activate.sh            # legacy HTTPS_PROXY mode (Task-1)
#   AGENTBOX_TRANSPARENT=1 source ~/agentbox/scripts/activate.sh  # transparent mode (Task-2)

_AB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_AB_CERT="$_AB_DIR/certs/agentbox-ca.crt"
_AB_PID="$_AB_DIR/.agentbox.pid"
_AB_LOG="$_AB_DIR/logs/agentbox-run.log"

# Generate CA if missing
if [ ! -f "$_AB_CERT" ]; then
    echo "[agentbox] CA not found — generating..."
    agentbox ca
fi

# Install CA into system trust store if not yet done
if ! openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt "$_AB_CERT" > /dev/null 2>&1; then
    echo "[agentbox] CA not in trust store — installing (requires sudo)..."
    bash "$_AB_DIR/scripts/install_ca.sh"
fi

# Start proxy if port 8080 is not already listening
if ! ss -ltnp 2>/dev/null | grep -q ':8080'; then
    echo "[agentbox] Starting proxy in background..."
    mkdir -p "$_AB_DIR/logs"
    if [ "${AGENTBOX_TRANSPARENT:-0}" = "1" ]; then
        nohup env TRANSPARENT_MODE=true agentbox run > "$_AB_LOG" 2>&1 &
    else
        nohup agentbox run > "$_AB_LOG" 2>&1 &
    fi
    echo $! > "$_AB_PID"
    # Wait up to 8 seconds for Web UI to come up
    for i in $(seq 1 8); do
        sleep 1
        if ss -ltnp 2>/dev/null | grep -q ':8000'; then
            break
        fi
    done
else
    echo "[agentbox] Proxy already running on :8080"
fi

# 1A-3: Transparent mode - set up iptables redirect, skip HTTPS_PROXY
if [ "${AGENTBOX_TRANSPARENT:-0}" = "1" ]; then
    echo "[agentbox] Enabling iptables transparent redirect (requires sudo) ..."
    sudo bash "$_AB_DIR/scripts/iptables_redirect.sh" on
    export NODE_EXTRA_CA_CERTS="$_AB_CERT"
    echo ""
    echo "  AgentBox activated (transparent mode)"
    echo "  iptables: uid=$(id -u) port 443 -> 8080"
    echo "  Web UI  : http://localhost:8000"
    echo "  Stats   : $_AB_DIR/logs/ebpf-stats.log"
    echo "  Log     : $_AB_LOG"
    echo "  Deactivate: source $_AB_DIR/scripts/deactivate.sh"
    echo ""
else
    export HTTPS_PROXY=http://127.0.0.1:8080
    export NODE_EXTRA_CA_CERTS="$_AB_CERT"
    echo ""
    echo "  AgentBox activated (HTTPS_PROXY mode)"
    echo "  Web UI : http://localhost:8000"
    echo "  Log    : $_AB_LOG"
    echo "  Deactivate: source $_AB_DIR/scripts/deactivate.sh"
    echo ""
fi
