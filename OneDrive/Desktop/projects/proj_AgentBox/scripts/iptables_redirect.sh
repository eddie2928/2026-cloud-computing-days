#!/usr/bin/env bash
# 1A-3: iptables transparent redirect - uid-based 443 -> 8080
# Usage:
#   sudo bash scripts/iptables_redirect.sh on   # enable redirect
#   sudo bash scripts/iptables_redirect.sh off  # disable redirect

set -e

PROXY_PORT="${AGENTBOX_PROXY_PORT:-8080}"
TARGET_UID="${AGENTBOX_UID:-$(id -u)}"

_rule_exists() {
    iptables -t nat -C OUTPUT -p tcp --dport 443 \
        -m owner --uid-owner "$TARGET_UID" \
        -j REDIRECT --to-port "$PROXY_PORT" 2>/dev/null
}

case "${1:-on}" in
    on)
        if _rule_exists; then
            echo "[agentbox] iptables REDIRECT already active (uid=$TARGET_UID -> :$PROXY_PORT)"
        else
            iptables -t nat -A OUTPUT -p tcp --dport 443 \
                -m owner --uid-owner "$TARGET_UID" \
                -j REDIRECT --to-port "$PROXY_PORT"
            echo "[agentbox] iptables REDIRECT active: uid=$TARGET_UID port 443 -> $PROXY_PORT"
        fi
        ;;
    off)
        if _rule_exists; then
            iptables -t nat -D OUTPUT -p tcp --dport 443 \
                -m owner --uid-owner "$TARGET_UID" \
                -j REDIRECT --to-port "$PROXY_PORT"
            echo "[agentbox] iptables REDIRECT removed"
        else
            echo "[agentbox] No REDIRECT rule found (uid=$TARGET_UID)"
        fi
        ;;
    *)
        echo "Usage: $0 {on|off}" >&2
        exit 1
        ;;
esac
