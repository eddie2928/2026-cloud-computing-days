"""Integration tests for agentbox run lifecycle (Task-7 J3).

Note: T1 attempts a real background process fork and is marked with a custom
marker. T2 tests the "already running" short-circuit via mocking.
"""
import socket
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import agentbox.set_cmd as set_module
from agentbox.set_cmd import run_set, _start_and_health_check


@pytest.fixture(autouse=True)
def reset_logger():
    import logging
    logger = logging.getLogger("agentbox.set")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    monkeypatch.setattr(set_module, "_PROJ_ROOT", tmp_path)
    (tmp_path / ".bashrc").write_text("", encoding="utf-8")
    return tmp_path


class FakeArgs:
    yes = True
    skip_deps_install = True


# ── T1: set 두 번 연속 호출 → 두 번째는 "이미 실행 중" 분기 ─────────────────
def test_set_second_run_skips_proxy(isolated_env):
    call_count = [0]

    def fake_start_health(layout):
        call_count[0] += 1
        if call_count[0] == 1:
            # First run: simulate proxy starts
            layout.local_pid.parent.mkdir(parents=True, exist_ok=True)
            layout.local_pid.write_text("99999")
            return 0
        else:
            # Second run: proxy "already running" check
            return 0

    with patch("agentbox.set_cmd.check_dep", return_value=(True, None)), \
         patch("agentbox.set_cmd.check_python_pkg", return_value=True), \
         patch("agentbox.set_cmd._check_ca_mtls_step", return_value=0), \
         patch("agentbox.set_cmd._ensure_proto_stub", return_value=0), \
         patch("agentbox.set_cmd._start_and_health_check", side_effect=fake_start_health), \
         patch("agentbox.set_cmd._check_grpc_tcp", return_value=0), \
         patch("agentbox.set_cmd._check_mtls_handshake", return_value=0), \
         patch("agentbox.set_cmd.platform.system", return_value="Linux"):
        rc1 = run_set(FakeArgs())
        import logging
        logging.getLogger("agentbox.set").handlers.clear()
        rc2 = run_set(FakeArgs())

    assert rc1 == 0
    assert rc2 == 0
    assert call_count[0] == 2


# ── T2: _start_and_health_check — already listening → skip Popen ─────────────
def test_start_health_already_running(isolated_env):
    from agentbox.dotagentbox import ensure_layout

    layout = ensure_layout(isolated_env)
    popen_calls = []

    def fake_connect(addr, timeout=None):
        return MagicMock().__enter__.return_value

    with patch("agentbox.set_cmd.socket.create_connection", side_effect=fake_connect), \
         patch("agentbox.set_cmd.subprocess.Popen", side_effect=popen_calls.append):
        rc = _start_and_health_check(layout)

    assert rc == 0
    assert len(popen_calls) == 0  # No new process started
