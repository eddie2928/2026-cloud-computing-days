import sys
import pytest
from unittest.mock import patch, MagicMock


def make_ok_result(stdout="", returncode=0):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = stdout
    r.stderr = ""
    return r


class TestRegister:
    def test_register_calls_schtasks_create(self):
        """register() must call schtasks /Create with /TN WinLayoutSaver_Rollback"""
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import register
            register(script_path="C:\\path\\to\\rollback.py", delay_seconds=20)
            assert mock_run.called
            args = mock_run.call_args[0][0]  # first positional arg (the command list)
            cmd_str = " ".join(str(a) for a in args)
            assert "/Create" in cmd_str or "/create" in cmd_str.lower()
            assert "WinLayoutSaver_Rollback" in cmd_str

    def test_register_includes_delay(self):
        """register() must encode delay_seconds as HH:MM in /DELAY"""
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import register
            register(script_path="C:\\path\\to\\rollback.py", delay_seconds=90)  # 1m30s
            args = mock_run.call_args[0][0]
            cmd_str = " ".join(str(a) for a in args)
            assert "0001:30" in cmd_str  # 90 seconds = 0h1m30s → 0001:30

    def test_register_delay_20_seconds(self):
        """20 seconds = 0000:20"""
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import register
            register(script_path="C:\\path\\to\\rollback.py", delay_seconds=20)
            args = mock_run.call_args[0][0]
            cmd_str = " ".join(str(a) for a in args)
            assert "0000:20" in cmd_str

    def test_register_uses_rl_limited(self):
        """/RL LIMITED — no admin rights required"""
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import register
            register(script_path="C:\\path\\to\\rollback.py", delay_seconds=20)
            args = mock_run.call_args[0][0]
            cmd_str = " ".join(str(a) for a in args)
            assert "/RL" in cmd_str and "LIMITED" in cmd_str

    def test_register_returns_true_on_success(self):
        with patch("subprocess.run", return_value=make_ok_result(returncode=0)):
            from src.scheduler import register
            result = register(script_path="C:\\path\\rollback.py", delay_seconds=20)
            assert result is True

    def test_register_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=make_ok_result(returncode=1)):
            from src.scheduler import register
            result = register(script_path="C:\\path\\rollback.py", delay_seconds=20)
            assert result is False


class TestUnregister:
    def test_unregister_calls_schtasks_delete(self):
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import unregister
            unregister()
            args = mock_run.call_args[0][0]
            cmd_str = " ".join(str(a) for a in args)
            assert "/Delete" in cmd_str or "/delete" in cmd_str.lower()
            assert "WinLayoutSaver_Rollback" in cmd_str

    def test_unregister_uses_force_flag(self):
        with patch("subprocess.run", return_value=make_ok_result()) as mock_run:
            from src.scheduler import unregister
            unregister()
            args = mock_run.call_args[0][0]
            cmd_str = " ".join(str(a) for a in args)
            assert "/F" in cmd_str

    def test_unregister_returns_true_on_success(self):
        with patch("subprocess.run", return_value=make_ok_result(returncode=0)):
            from src.scheduler import unregister
            assert unregister() is True

    def test_unregister_returns_false_on_failure(self):
        with patch("subprocess.run", return_value=make_ok_result(returncode=1)):
            from src.scheduler import unregister
            assert unregister() is False
