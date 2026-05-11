"""Unit tests for src/agentbox/status_cmd.py."""
import json
import socket
from unittest.mock import MagicMock, patch

import pytest

import agentbox.status_cmd as status_module
from agentbox.status_cmd import (
    _get_connectivity,
    _get_deps_status,
    _get_last_init,
    _get_proxy_state,
    _get_saas_url,
    run_status,
)


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.status")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


class FakeArgs:
    def __init__(self, json_output=False):
        self.json = json_output


def test_get_saas_url_from_last_init(monkeypatch):
    meta = {"saas_url": "http://1.2.3.4:8000", "project_id": "test"}

    with patch.object(status_module.last_init, "read", return_value=meta):
        url = _get_saas_url()

    assert url == "http://1.2.3.4:8000"


def test_get_saas_url_fallback_terraform(monkeypatch):
    with patch.object(status_module.last_init, "read", return_value=None), \
         patch.object(status_module, "get_terraform_output", return_value="http://5.6.7.8:8000"):
        url = _get_saas_url()

    assert url == "http://5.6.7.8:8000"


def test_get_saas_url_returns_none_when_all_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(status_module, "_PROJ_ROOT", tmp_path)

    with patch.object(status_module.last_init, "read", return_value=None), \
         patch.object(status_module, "get_terraform_output", return_value=None):
        url = _get_saas_url()

    assert url is None


def test_get_deps_status_all_ok(monkeypatch):
    monkeypatch.setattr(status_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)

    result = _get_deps_status()
    assert all(result.values())
    assert "sops" in result
    assert "aws" in result


def test_get_deps_status_sops_missing(monkeypatch):
    def fake_check_dep(dep):
        return (False, "not found") if dep.name == "sops" else (True, None)

    monkeypatch.setattr(status_module, "check_dep", fake_check_dep)
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)

    result = _get_deps_status()
    assert result["sops"] is False
    assert result["aws"] is True


def test_get_proxy_state_on(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8080")

    with patch("agentbox.status_cmd.socket.create_connection"):
        state = _get_proxy_state()

    assert state["https_proxy_env"] == "http://127.0.0.1:8080"
    assert state["listening_8080"] is True


def test_get_proxy_state_off(monkeypatch):
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)

    with patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")):
        state = _get_proxy_state()

    assert state["https_proxy_env"] is None
    assert state["listening_8080"] is False


def test_run_status_includes_footer(capsys):
    with patch.object(status_module, "_get_saas_url", return_value="http://1.2.3.4:8000"), \
         patch.object(status_module, "_get_deps_status", return_value={"sops": True, "aws": True, "boto3": True, "pyyaml": True}), \
         patch.object(status_module, "_get_proxy_state", return_value={"https_proxy_env": None, "listening_8080": False}), \
         patch.object(status_module, "_get_last_init", return_value=None), \
         patch.object(status_module, "_get_connectivity", return_value={"saas_healthz": 200, "grpc_tcp": True}):

        rc = run_status(FakeArgs(json_output=False))

    assert rc == 0
    captured = capsys.readouterr()
    assert "Made by JeonMyeonghwan" in captured.out


def test_run_status_json_no_footer_in_stdout(capsys):
    with patch.object(status_module, "_get_saas_url", return_value="http://1.2.3.4:8000"), \
         patch.object(status_module, "_get_deps_status", return_value={"sops": True}), \
         patch.object(status_module, "_get_proxy_state", return_value={"https_proxy_env": None, "listening_8080": False}), \
         patch.object(status_module, "_get_last_init", return_value=None), \
         patch.object(status_module, "_get_connectivity", return_value={}):

        rc = run_status(FakeArgs(json_output=True))

    assert rc == 0
    captured = capsys.readouterr()
    # Footer must NOT appear in JSON mode stdout
    assert "Made by JeonMyeonghwan" not in captured.out
    # JSON must be parseable and contain meta.author
    data = json.loads(captured.out)
    assert data["meta"]["author"] == "JeonMyeonghwan"


def test_get_saas_url_from_env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(status_module, "_PROJ_ROOT", tmp_path)
    env_file = tmp_path / ".env.endpoint"
    env_file.write_text("EC2_GRPC_HOST=10.0.0.1\n", encoding="utf-8")

    with patch.object(status_module.last_init, "read", return_value=None), \
         patch.object(status_module, "get_terraform_output", return_value=None):
        url = _get_saas_url()

    assert url == "http://10.0.0.1:8000"


def test_get_connectivity_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("agentbox.status_cmd.requests.get", return_value=mock_resp), \
         patch("agentbox.status_cmd.socket.create_connection"):
        result = _get_connectivity("http://1.2.3.4:8000", "1.2.3.4")

    assert result["saas_healthz"] == 200
    assert result["grpc_tcp"] is True


def test_get_connectivity_no_url_no_host():
    result = _get_connectivity(None, None)
    assert result["saas_healthz"] == "URL unknown"
    assert result["grpc_tcp"] == "host unknown"


def test_get_connectivity_failure():
    with patch("agentbox.status_cmd.requests.get", side_effect=Exception("refused")), \
         patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")):
        result = _get_connectivity("http://1.2.3.4:8000", "1.2.3.4")

    assert "ERROR" in str(result["saas_healthz"])
    assert "ERROR" in str(result["grpc_tcp"])


def test_run_status_with_last_init(capsys):
    meta = {
        "project_id": "myrepo",
        "src_path": "/home/user/myrepo",
        "s3_uri": "s3://bucket/encrypted_code/myrepo/",
        "uploaded_at": "2026-05-11T03:21:18+00:00",
        "saas_url": "http://1.2.3.4:8000",
    }

    with patch.object(status_module, "_get_saas_url", return_value="http://1.2.3.4:8000"), \
         patch.object(status_module, "_get_deps_status", return_value={"sops": True}), \
         patch.object(status_module, "_get_proxy_state", return_value={"https_proxy_env": "http://127.0.0.1:8080", "listening_8080": True}), \
         patch.object(status_module, "_get_last_init", return_value=meta), \
         patch.object(status_module, "_get_connectivity", return_value={"saas_healthz": 200, "grpc_tcp": True}):

        rc = run_status(FakeArgs(json_output=False))

    assert rc == 0
    out = capsys.readouterr().out
    assert "myrepo" in out
    assert "s3://bucket" in out
    assert "ON" in out


def test_run_status_no_previous_init(capsys):
    with patch.object(status_module, "_get_saas_url", return_value=None), \
         patch.object(status_module, "_get_deps_status", return_value={}), \
         patch.object(status_module, "_get_proxy_state", return_value={"https_proxy_env": None, "listening_8080": False}), \
         patch.object(status_module, "_get_last_init", return_value=None), \
         patch.object(status_module, "_get_connectivity", return_value={}):

        rc = run_status(FakeArgs(json_output=False))

    assert rc == 0
    captured = capsys.readouterr()
    assert "No previous init" in captured.out
