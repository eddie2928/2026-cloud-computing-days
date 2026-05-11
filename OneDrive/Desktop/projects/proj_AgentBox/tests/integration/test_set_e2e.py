"""Integration tests for agentbox set end-to-end."""
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import agentbox.set_cmd as set_module
from agentbox.set_cmd import run_set


class FakeArgs:
    def __init__(self, yes=True, skip_deps_install=True):
        self.yes = yes
        self.skip_deps_install = skip_deps_install


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.set")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")
    monkeypatch.setattr(set_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "logs").mkdir()
    return tmp_path


def test_set_idempotent(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        run_set(FakeArgs())
        content_first = (tmp_home / ".bashrc").read_text(encoding="utf-8")
        run_set(FakeArgs())
        content_second = (tmp_home / ".bashrc").read_text(encoding="utf-8")

    assert content_first == content_second


def test_set_writes_env_exports(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        run_set(FakeArgs())

    content = (tmp_home / ".bashrc").read_text(encoding="utf-8")
    assert "export AWS_REGION=" in content
    assert "export PROJECT_NAME=" in content


def test_set_does_not_auto_activate(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        run_set(FakeArgs())

    content = (tmp_home / ".bashrc").read_text(encoding="utf-8")
    assert "export HTTPS_PROXY=" not in content


def test_set_registers_shell_functions(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        run_set(FakeArgs())

    content = (tmp_home / ".bashrc").read_text(encoding="utf-8")
    assert "# AgentBox shell integration" in content
    assert "agentbox()" in content
    assert "on)" in content
    assert "off)" in content


def test_set_returns_zero_on_success(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs())

    assert rc == 0
