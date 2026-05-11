"""라이브 EC2 SaaS (/api/*) 통합 테스트. SKIP_LIVE=1 환경변수로 건너뛸 수 있음."""
import os
import json
import socket
from urllib.parse import urlparse

import pytest
import httpx
from websockets.sync.client import connect as ws_connect


LIVE_URL = os.environ.get("LIVE_SAAS_URL", "http://54.165.51.239:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
SKIP = os.environ.get("SKIP_LIVE", "0") == "1"


pytestmark = pytest.mark.skipif(
    SKIP or not ADMIN_TOKEN,
    reason="SKIP_LIVE=1 or ADMIN_TOKEN not set",
)


def test_healthz():
    r = httpx.get(f"{LIVE_URL}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_audit_html_no_token():
    r = httpx.get(f"{LIVE_URL}/audit", timeout=5)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_api_audit_requires_token():
    r = httpx.get(f"{LIVE_URL}/api/audit", timeout=5)
    assert r.status_code == 401


def test_api_audit_with_token_returns_list():
    r = httpx.get(
        f"{LIVE_URL}/api/audit?limit=1",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_settings_prompt_get():
    r = httpx.get(
        f"{LIVE_URL}/api/settings/prompt-get",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10,
    )
    assert r.status_code == 200
    assert "system_prompt" in r.json()


def test_api_settings_kb_ttl_get():
    r = httpx.get(
        f"{LIVE_URL}/api/settings/kb-ttl-get",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        timeout=10,
    )
    assert r.status_code == 200
    assert "ttl_minutes" in r.json()


def test_api_pipeline_stream_ws_handshake():
    """WebSocket /api/pipeline/stream 핸드셰이크가 성공해야 한다."""
    parsed = urlparse(LIVE_URL)
    ws_url = f"ws://{parsed.netloc}/api/pipeline/stream"
    with ws_connect(ws_url, open_timeout=5) as ws:
        # 즉시 메시지를 받지 못해도 핸드셰이크만 검증
        assert ws.protocol is not None
