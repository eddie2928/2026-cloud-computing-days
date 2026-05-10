"""Unit tests for lambda/mcp_bridge.py (uses urllib.request, not requests)."""
import importlib.util
import json
import pathlib
import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO


MCP_BASE = "http://mcp-test:8080"
ADMIN_TOKEN = "bridge-token"


def _load_handler():
    """Import mcp_bridge from the lambda/ directory (avoids 'lambda' keyword issue)."""
    spec = importlib.util.spec_from_file_location(
        "mcp_bridge",
        pathlib.Path(__file__).parents[2] / "lambda" / "mcp_bridge.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.handler


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", MCP_BASE)
    monkeypatch.setenv("MCP_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("KB_STAGING_BUCKET", "agentbox-kb-staging")


def _make_event(project_id="default"):
    return {
        "actionGroup": "decrypt_and_stage",
        "function": "decrypt_and_stage",
        "messageVersion": "1.0",
        "sessionId": "test-session-123",
        "parameters": [{"name": "project_id", "value": project_id}],
    }


def _mock_response(body_dict):
    """Create a mock urllib response context manager."""
    body = json.dumps(body_dict).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_handler_calls_mcp_and_returns_response():
    handler = _load_handler()
    expected = {"kb_bucket": "agentbox-kb-staging", "prefix": "staging/test/"}

    with patch("urllib.request.urlopen", return_value=_mock_response(expected)) as mock_open:
        result = handler(_make_event(), None)

    assert mock_open.called
    body_str = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    body = json.loads(body_str)
    assert body["kb_bucket"] == "agentbox-kb-staging"


def test_authorization_header_present():
    handler = _load_handler()

    captured_req = {}

    def capture_open(req, timeout=None):
        captured_req["req"] = req
        return _mock_response({"kb_bucket": "b", "prefix": "p"})

    with patch("urllib.request.urlopen", side_effect=capture_open):
        handler(_make_event(), None)

    req = captured_req["req"]
    auth_header = req.get_header("Authorization")
    assert auth_header == f"Bearer {ADMIN_TOKEN}"


def test_response_format_matches_bedrock_action_group():
    handler = _load_handler()

    with patch("urllib.request.urlopen", return_value=_mock_response({"kb_bucket": "b", "prefix": "p"})):
        event = _make_event()
        result = handler(event, None)

    assert result["response"]["actionGroup"] == event["actionGroup"]
    assert result["response"]["function"] == event["function"]
    assert "TEXT" in result["response"]["functionResponse"]["responseBody"]
