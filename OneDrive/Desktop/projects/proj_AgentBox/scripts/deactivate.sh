#!/usr/bin/env bash
# Source this file to deactivate AgentBox and stop the proxy.
# Usage: source ~/agentbox/scripts/deactivate.sh

_AB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_AB_PID="$_AB_DIR/.agentbox.pid"

# Remove iptables redirect rule if active (1A-3)
if sudo bash "$_AB_DIR/scripts/iptables_redirect.sh" off 2>/dev/null; then
    :
fi

# Stop background proxy if we started it
if [ -f "$_AB_PID" ]; then
    _PID=$(cat "$_AB_PID")
    if kill -0 "$_PID" 2>/dev/null; then
        echo "[agentbox] Stopping proxy (pid $_PID)..."
        kill "$_PID"
    fi
    rm -f "$_AB_PID"
fi

unset HTTPS_PROXY
unset NODE_EXTRA_CA_CERTS

echo "[agentbox] Deactivated. claude will connect directly to Anthropic."
