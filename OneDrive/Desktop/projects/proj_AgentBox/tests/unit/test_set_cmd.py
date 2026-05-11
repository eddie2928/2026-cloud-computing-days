"""Unit tests for src/agentbox/set_cmd.py."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import agentbox.set_cmd as set_module
from agentbox.set_cmd import (
    _check_deps_step,
    _check_env_step,
    _install_shell_integration,
    run_set,
)


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
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")
    monkeypatch.setattr(set_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "logs").mkdir()
    return tmp_path


class FakeArgs:
    def __init__(self, yes=False, skip_deps_install=False):
        self.yes = yes
        self.skip_deps_install = skip_deps_install


def test_step1_deps_all_present(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    install_calls = []
    monkeypatch.setattr(set_module, "try_auto_install", lambda d: install_calls.append(d) or True)

    rc = _check_deps_step(FakeArgs())
    assert rc == 0
    assert len(install_calls) == 0


def test_step1_deps_missing_no_install(tmp_home, monkeypatch):
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (False, "not found"))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)
    monkeypatch.setattr(set_module, "try_auto_install", lambda d: True)

    rc = _check_deps_step(FakeArgs(skip_deps_install=True))
    # skip_deps_install=True → warn only, continue (return 0)
    assert rc == 0


def test_step2_env_missing(tmp_home, monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    bashrc = tmp_home / ".bashrc"
    rc = _check_env_step(FakeArgs(yes=True), bashrc)

    assert rc == 0
    content = bashrc.read_text(encoding="utf-8")
    assert "export AWS_REGION=us-east-1" in content


def test_step2_idempotent(tmp_home, monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)

    bashrc = tmp_home / ".bashrc"

    _check_env_step(FakeArgs(yes=True), bashrc)
    count_after_first = bashrc.read_text(encoding="utf-8").count("export AWS_REGION=")

    _check_env_step(FakeArgs(yes=True), bashrc)
    count_after_second = bashrc.read_text(encoding="utf-8").count("export AWS_REGION=")

    assert count_after_first == count_after_second == 1


def test_step3_ca_missing(tmp_home, monkeypatch):
    # _PROJ_ROOT is already monkeypatched to tmp_home in the fixture.
    # cfg.CA_DIR defaults to "certs" (relative), so ca_dir = tmp_home / "certs".
    with patch("agentbox.set_cmd.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        from agentbox.set_cmd import _check_ca_step
        rc = _check_ca_step()

    assert rc == 0
    assert (tmp_home / "certs" / "agentbox-ca.crt").exists()


def test_step4_shell_integration(tmp_home, monkeypatch):
    bashrc = tmp_home / ".bashrc"
    result = _install_shell_integration(bashrc)

    assert result is True
    content = bashrc.read_text(encoding="utf-8")
    assert "# AgentBox shell integration" in content
    assert "agentbox()" in content


def test_step4_shell_integration_idempotent(tmp_home, monkeypatch):
    bashrc = tmp_home / ".bashrc"
    _install_shell_integration(bashrc)
    result_second = _install_shell_integration(bashrc)

    assert result_second is False
    content = bashrc.read_text(encoding="utf-8")
    assert content.count("# AgentBox shell integration") == 1


def test_no_auto_activation_added(tmp_home, monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    monkeypatch.setattr(set_module, "check_dep", lambda dep: (True, None))
    monkeypatch.setattr(set_module, "check_python_pkg", lambda pkg: True)

    with patch("agentbox.set_cmd._check_ca_step", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs(yes=True, skip_deps_install=True))

    assert rc == 0
    bashrc = tmp_home / ".bashrc"
    content = bashrc.read_text(encoding="utf-8")

    # HTTPS_PROXY must NOT be automatically exported
    assert "export HTTPS_PROXY=" not in content
    # No standalone 'agentbox on' call outside function body
    lines = content.splitlines()
    in_func = False
    for line in lines:
        stripped = line.strip()
        if "agentbox() {" in stripped or "agentbox(){" in stripped:
            in_func = True
        if in_func and stripped == "}":
            in_func = False
        if not in_func and stripped == "agentbox on":
            pytest.fail(f"Found auto-activation 'agentbox on' outside function: {line!r}")
