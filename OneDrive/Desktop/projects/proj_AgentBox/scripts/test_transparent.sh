#!/usr/bin/env bash
# 1A-6, 1A-7: Integration tests for transparent proxy mode
# Run inside VM AFTER iptables redirect and agentbox proxy are active.
# Prerequisite: agentbox running in transparent mode (AGENTBOX_TRANSPARENT=1 agentbox run)

set -e

PROXY_PORT="${AGENTBOX_PROXY_PORT:-8080}"
MITMPROXY_LOG="${AGENTBOX_MITMPROXY_LOG:-/tmp/mitmproxy-access.log}"

pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }

echo ""
echo "=== AgentBox Transparent Proxy Integration Tests ==="
echo ""

# Sanity check: proxy is listening
if ! ss -ltnp 2>/dev/null | grep -q ":${PROXY_PORT}"; then
    fail "Proxy not listening on :${PROXY_PORT}. Start with: AGENTBOX_TRANSPARENT=1 agentbox run"
fi
pass "Proxy listening on :${PROXY_PORT}"

# 1A-6: Anthropic traffic captured (HTTPS_PROXY must NOT be set)
if [ -n "$HTTPS_PROXY" ]; then
    fail "HTTPS_PROXY is set. Unset it to test transparent mode: unset HTTPS_PROXY"
fi

# Snapshot current log line count
LOG_BEFORE=$(wc -l < "$MITMPROXY_LOG" 2>/dev/null || echo 0)

echo "  Sending test request to api.anthropic.com/healthcheck (no HTTPS_PROXY) ..."
curl --max-time 10 -sk "https://api.anthropic.com/healthcheck" -o /dev/null || true

sleep 1
LOG_AFTER=$(wc -l < "$MITMPROXY_LOG" 2>/dev/null || echo 0)

if [ "$LOG_AFTER" -gt "$LOG_BEFORE" ]; then
    pass "1A-6: api.anthropic.com request captured in mitmproxy log"
else
    fail "1A-6: api.anthropic.com request NOT captured. Check iptables redirect and proxy mode."
fi

# 1A-7: Non-target traffic passes through unaffected
LOG_BEFORE2=$(wc -l < "$MITMPROXY_LOG" 2>/dev/null || echo 0)
echo "  Sending request to www.google.com ..."
curl --max-time 10 -sk "https://www.google.com" -o /dev/null || true

sleep 1
LOG_AFTER2=$(wc -l < "$MITMPROXY_LOG" 2>/dev/null || echo 0)

if [ "$LOG_AFTER2" -eq "$LOG_BEFORE2" ]; then
    pass "1A-7: www.google.com traffic NOT captured (pass-through OK)"
else
    fail "1A-7: www.google.com traffic captured — SNI filter not working."
fi

echo ""
echo "=== Phase 1A Gate: PASSED ==="
echo ""
