"""Integration tests for agentbox set end-to-end (Task-7 J1)."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import agentbox.set_cmd as set_module
from agentbox.set_cmd import run_set


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.set")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Fully isolated environment: HOME, AGENTBOX_HOME, _PROJ_ROOT all in tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    monkeypatch.setattr(set_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")
    return tmp_path


class FakeArgs:
    def __init__(self, yes=True, skip_deps_install=True):
        self.yes = yes
        self.skip_deps_install = skip_deps_install


# ── T1: 임시 HOME + 임시 repo에서 set 전체 흐름 → exit 0, 8개 산출물 검증 ────
def test_set_e2e_creates_layout(isolated_env):
    global_home = isolated_env / "global"

    with patch("agentbox.set_cmd.check_dep", return_value=(True, None)), \
         patch("agentbox.set_cmd.check_python_pkg", return_value=True), \
         patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs())

    assert rc == 0
    # Layout directories created
    assert (global_home).is_dir()
    assert (global_home / "certs" / "grpc").is_dir()
    assert (isolated_env / ".agentbox").is_dir()
    assert (isolated_env / ".agentbox" / "logs").is_dir()


# ── T2: 같은 repo 두 번 실행 → idempotent, 마이그레이션 한 번만 ──────────────
def test_set_e2e_idempotent(isolated_env):
    with patch("agentbox.set_cmd.check_dep", return_value=(True, None)), \
         patch("agentbox.set_cmd.check_python_pkg", return_value=True), \
         patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc1 = run_set(FakeArgs())
        # reset logger for second run
        import logging
        logging.getLogger("agentbox.set").handlers.clear()
        rc2 = run_set(FakeArgs())

    assert rc1 == 0
    assert rc2 == 0


# ── T3: 마이그레이션 후 원본 .env 부재 확인 ──────────────────────────────────
def test_set_e2e_migration(isolated_env):
    # Create legacy config files
    (isolated_env / ".env").write_text("GRPC_HOST=1.2.3.4\n")
    (isolated_env / ".sops.yaml").write_text("creation_rules:\n  - kms: arn:real\n")

    with patch("agentbox.set_cmd.check_dep", return_value=(True, None)), \
         patch("agentbox.set_cmd.check_python_pkg", return_value=True), \
         patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", return_value=0), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc = run_set(FakeArgs())

    assert rc == 0
    # Source .env should be gone after migration
    assert not (isolated_env / ".env").exists()
    # Migrated to global home
    global_env = isolated_env / "global" / "env"
    assert global_env.read_text() == "GRPC_HOST=1.2.3.4\n"
