"""Unit tests for src/agentbox/init_deps.py."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agentbox.init_deps import DEPS, check_dep, check_python_pkg, try_auto_install


def test_check_dep_present():
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("agentbox.init_deps.subprocess.run", return_value=mock_result):
        ok, err = check_dep(DEPS[0])
    assert ok is True
    assert err is None


def test_check_dep_nonzero():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b"command not found"
    with patch("agentbox.init_deps.subprocess.run", return_value=mock_result):
        ok, err = check_dep(DEPS[0])
    assert ok is False
    assert "command not found" in err


def test_check_dep_missing_file():
    with patch("agentbox.init_deps.subprocess.run", side_effect=FileNotFoundError("not found")):
        ok, err = check_dep(DEPS[0])
    assert ok is False
    assert err is not None


def test_try_auto_install_success():
    dep = DEPS[0]
    install_result = MagicMock()
    install_result.returncode = 0
    check_success = MagicMock()
    check_success.returncode = 0

    with patch("agentbox.init_deps.subprocess.run", side_effect=[install_result, check_success]):
        result = try_auto_install(dep)
    assert result is True


def test_try_auto_install_fail():
    dep = DEPS[0]
    install_result = MagicMock()
    install_result.returncode = 0
    check_fail = MagicMock()
    check_fail.returncode = 1
    check_fail.stderr = b"still missing"

    with patch("agentbox.init_deps.subprocess.run", side_effect=[install_result, check_fail]):
        result = try_auto_install(dep)
    assert result is False


def test_check_python_pkg_present():
    with patch("agentbox.init_deps.importlib.metadata.version", return_value="1.0.0"):
        assert check_python_pkg("boto3") is True


def test_check_python_pkg_missing():
    import importlib.metadata
    with patch("agentbox.init_deps.importlib.metadata.version",
               side_effect=importlib.metadata.PackageNotFoundError("not found")):
        assert check_python_pkg("nonexistent-pkg") is False
