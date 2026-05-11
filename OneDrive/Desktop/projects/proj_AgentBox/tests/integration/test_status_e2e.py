"""Integration tests for agentbox status end-to-end."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import agentbox.status_cmd as status_module
from agentbox.status_cmd import run_status
from agentbox import last_init


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


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(status_module, "_PROJ_ROOT", tmp_path)
    return tmp_path


def test_status_no_last_init(tmp_home, monkeypatch, capsys):
    monkeypatch.setattr(status_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("https_proxy", raising=False)

    with patch.object(status_module.last_init, "read", return_value=None), \
         patch.object(status_module, "get_terraform_output", return_value=None), \
         patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")):
        rc = run_status(FakeArgs())

    assert rc == 0
    out = capsys.readouterr().out
    assert "No previous init" in out
    assert "Made by JeonMyeonghwan" in out


def test_status_with_last_init(tmp_home, monkeypatch, capsys):
    meta = {
        "project_id": "myrepo",
        "src_path": "/home/user/myrepo",
        "s3_uri": "s3://bucket/encrypted_code/myrepo/",
        "uploaded_at": "2026-05-11T03:21:18+00:00",
        "saas_url": "http://54.165.51.239:8000",
    }
    monkeypatch.setattr(status_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    with patch.object(status_module.last_init, "read", return_value=meta), \
         patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")), \
         patch("agentbox.status_cmd.requests.get", side_effect=Exception("unreachable")):
        rc = run_status(FakeArgs())

    assert rc == 0
    out = capsys.readouterr().out
    assert "myrepo" in out
    assert "2026-05-11" in out
    assert "54.165.51.239" in out


def test_status_json_output(tmp_home, monkeypatch, capsys):
    monkeypatch.setattr(status_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    with patch.object(status_module.last_init, "read", return_value=None), \
         patch.object(status_module, "get_terraform_output", return_value=None), \
         patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")):
        rc = run_status(FakeArgs(json_output=True))

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["meta"]["author"] == "JeonMyeonghwan"


def test_status_connectivity_failures_dont_crash(tmp_home, monkeypatch, capsys):
    monkeypatch.setattr(status_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(status_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    with patch.object(status_module.last_init, "read", return_value={"saas_url": "http://999.999.999.999:8000"}), \
         patch("agentbox.status_cmd.socket.create_connection", side_effect=OSError("refused")), \
         patch("agentbox.status_cmd.requests.get", side_effect=Exception("Connection refused")):
        rc = run_status(FakeArgs())

    assert rc == 0
    out = capsys.readouterr().out
    assert "ERROR" in out or "refused" in out.lower()
