import pytest
import os
from pathlib import Path


@pytest.fixture
def tmp_appdata(tmp_path, monkeypatch):
    """Redirect APPDATA to a temp directory for tests."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # Also patch the module-level constants in storage
    import src.storage as storage_mod
    storage_mod.APPDATA = tmp_path / "WinLayoutSaver"
    storage_mod.LAYOUTS_DIR = tmp_path / "WinLayoutSaver" / "layouts"
    storage_mod.CONFIG_PATH = tmp_path / "WinLayoutSaver" / "config.json"
    return tmp_path
