"""Unit tests for lambda/mcp_bridge.py v2 (list_project_files / decrypt_and_stage routing)."""
import importlib.util
import json
import pathlib
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

MCP_BASE = "http://mcp-test:8080"
ADMIN_TOKEN = "bridge-v2-token"


def _load_handler():
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


def _mock_urlopen(body_str: str):
    mock_resp = MagicMock()
    mock_resp.read.return_value = body_str.encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_route_list_project_files():
    handler = _load_handler()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return _mock_urlopen("# Project files: demo\nTotal: 2 files, 100 bytes encrypted\n")

    event = {
        "actionGroup": "list_project_files",
        "function": "list_project_files",
        "parameters": [{"name": "project_id", "value": "demo"}],
    }
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = handler(event, None)

    assert captured["method"] == "GET"
    assert "/mcp/list_files/demo" in captured["url"]
    body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    assert "# Project files: demo" in body


def test_route_decrypt_and_stage():
    handler = _load_handler()
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data)
        return _mock_urlopen(json.dumps({"project_id": "demo", "files": []}))

    event = {
        "actionGroup": "decrypt_and_stage",
        "function": "decrypt_and_stage",
        "parameters": [
            {"name": "project_id", "value": "demo"},
            {"name": "files", "value": "src/main.py,config.yaml"},
            {"name": "start_byte", "value": "0"},
            {"name": "max_bytes", "value": "20480"},
        ],
    }
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = handler(event, None)

    assert captured["method"] == "POST"
    assert "/mcp/decrypt_and_stage" in captured["url"]
    assert captured["body"]["files"] == ["src/main.py", "config.yaml"]
    assert captured["body"]["start_byte"] == 0
    assert captured["body"]["max_bytes"] == 20480


def test_unknown_function():
    handler = _load_handler()
    event = {
        "actionGroup": "some_group",
        "function": "bogus_function",
        "parameters": [],
    }
    result = handler(event, None)
    body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    data = json.loads(body)
    assert "error" in data
    assert "bogus_function" in data["error"]


def test_authorization_header_present():
    handler = _load_handler()
    captured_headers = {}

    def capture_urlopen(req, timeout=None):
        captured_headers["auth"] = req.get_header("Authorization")
        return _mock_urlopen("# files\n")

    event = {
        "actionGroup": "list_project_files",
        "function": "list_project_files",
        "parameters": [{"name": "project_id", "value": "proj"}],
    }
    with patch("urllib.request.urlopen", side_effect=capture_urlopen):
        handler(event, None)

    assert captured_headers["auth"] == f"Bearer {ADMIN_TOKEN}"
