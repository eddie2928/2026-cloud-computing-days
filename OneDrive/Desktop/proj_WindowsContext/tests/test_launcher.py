"""Tests for src/launcher.py — mocks psutil and subprocess."""
import sys
import types
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc_info(exe: str):
    """Return a mock psutil Process with info dict."""
    p = MagicMock()
    p.info = {"exe": exe}
    return p


def _saved_window(
    exe_path="C:\\app.exe",
    exe_args="",
    cwd="",
    is_uwp=False,
    title_pattern="",
):
    return {
        "exe_path": exe_path,
        "exe_args": exe_args,
        "cwd": cwd,
        "is_uwp": is_uwp,
        "title_pattern": title_pattern,
    }


def _running_window(exe_path="C:\\app.exe", title="App Window"):
    return {
        "exe_path": exe_path,
        "title_snapshot": title,
    }


# ---------------------------------------------------------------------------
# is_running tests
# ---------------------------------------------------------------------------

def test_is_running_true(monkeypatch):
    """Process with matching exe_path is running."""
    import psutil
    mock_proc = _make_proc_info("C:\\app.exe")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [mock_proc])

    from src.launcher import is_running
    assert is_running("C:\\app.exe") is True


def test_is_running_false(monkeypatch):
    """No process with that exe_path."""
    import psutil
    mock_proc = _make_proc_info("C:\\other.exe")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [mock_proc])

    from src.launcher import is_running
    assert is_running("C:\\app.exe") is False


def test_is_running_case_insensitive(monkeypatch):
    """exe path match is case-insensitive."""
    import psutil
    mock_proc = _make_proc_info("C:\\App.EXE")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [mock_proc])

    from src.launcher import is_running
    assert is_running("c:\\app.exe") is True


# ---------------------------------------------------------------------------
# launch_app tests
# ---------------------------------------------------------------------------

def test_launch_app_calls_popen(monkeypatch):
    """When app not running, Popen is called with correct args."""
    mock_popen = MagicMock()
    mock_popen.return_value = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    from src.launcher import launch_app
    result = launch_app("C:\\app.exe", exe_args="--flag val")

    mock_popen.assert_called_once()
    cmd_arg = mock_popen.call_args[0][0]
    assert cmd_arg[0] == "C:\\app.exe"
    assert "--flag" in cmd_arg
    assert "val" in cmd_arg
    assert result is not None


def test_launch_app_not_called_when_running(monkeypatch):
    """When app already running, Popen is not called (caller is responsible)."""
    import psutil
    mock_proc = _make_proc_info("C:\\app.exe")
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [mock_proc])

    mock_popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    from src.launcher import is_running
    # is_running returns True; caller should not call launch_app
    assert is_running("C:\\app.exe") is True
    mock_popen.assert_not_called()


# ---------------------------------------------------------------------------
# wait_for_window tests
# ---------------------------------------------------------------------------

def test_wait_for_window_found(monkeypatch):
    """list_current_windows returns matching window on 2nd poll."""
    call_count = {"n": 0}

    def fake_list():
        call_count["n"] += 1
        if call_count["n"] < 2:
            return []
        return [_running_window("C:\\app.exe", "App Window")]

    monkeypatch.setattr("src.launcher.list_current_windows", fake_list)
    monkeypatch.setattr("time.sleep", lambda _: None)

    from src.launcher import wait_for_window
    result = wait_for_window("C:\\app.exe", title_pattern="App.*", timeout_seconds=10, poll_ms=50)
    assert result is True


def test_wait_for_window_timeout(monkeypatch):
    """Returns empty list every time; verify timeout after N retries."""
    call_count = {"n": 0}

    def fake_list():
        call_count["n"] += 1
        return []

    # Use a very short timeout and patch time.monotonic to advance quickly
    tick = {"t": 0.0}

    def fake_monotonic():
        val = tick["t"]
        tick["t"] += 0.6  # advance 600ms each call (past poll_ms=500)
        return val

    monkeypatch.setattr("src.launcher.list_current_windows", fake_list)
    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setattr("time.monotonic", fake_monotonic)

    from src.launcher import wait_for_window
    result = wait_for_window("C:\\app.exe", title_pattern="", timeout_seconds=1.0, poll_ms=500)
    assert result is False
    # Must have polled at least once
    assert call_count["n"] >= 1


# ---------------------------------------------------------------------------
# ensure_apps_running tests
# ---------------------------------------------------------------------------

def test_ensure_apps_running_launches_missing(monkeypatch):
    """2 saved windows, 1 already running, 1 not; verify only 1 launch."""
    import psutil

    running_exe = "C:\\running.exe"
    missing_exe = "C:\\missing.exe"

    def fake_process_iter(attrs):
        p = _make_proc_info(running_exe)
        return [p]

    monkeypatch.setattr(psutil, "process_iter", fake_process_iter)

    launched = []

    def fake_launch_app(exe_path, exe_args="", cwd="", is_uwp=False):
        launched.append(exe_path)
        return MagicMock()

    monkeypatch.setattr("src.launcher.launch_app", fake_launch_app)
    monkeypatch.setattr("src.launcher.wait_for_window", lambda *a, **kw: True)

    from src.launcher import ensure_apps_running
    saved = [
        _saved_window(exe_path=running_exe),
        _saved_window(exe_path=missing_exe),
    ]
    ensure_apps_running(saved, timeout_seconds=5, poll_ms=50)

    assert launched == [missing_exe]


def test_uwp_uses_explorer_shell(monkeypatch):
    """Saved window with is_uwp=True and AUMID in exe_args uses explorer.exe shell:AppsFolder."""
    mock_popen = MagicMock()
    mock_popen.return_value = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    aumid = "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"

    from src.launcher import launch_app
    launch_app("C:\\Windows\\ApplicationFrameHost.exe", exe_args=aumid, is_uwp=True)

    mock_popen.assert_called_once()
    cmd_arg = mock_popen.call_args[0][0]
    assert cmd_arg[0] == "explorer.exe"
    assert f"shell:AppsFolder\\{aumid}" in cmd_arg
