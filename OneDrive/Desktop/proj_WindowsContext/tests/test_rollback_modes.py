"""Task-11: rollback fast/full mode 분기 검증."""
import sys
import types
from unittest.mock import patch, MagicMock


def _stub_win32(monkeypatch):
    """rollback.py가 의존하는 win32 관련 모듈을 가짜로 등록."""
    win32gui = types.ModuleType("win32gui")
    win32con = types.ModuleType("win32con")
    win32con.SW_SHOWNORMAL = 1
    win32con.SW_SHOWMINIMIZED = 2
    win32con.SW_SHOWMAXIMIZED = 3
    win32gui.SetWindowPlacement = lambda *a: None
    win32gui.SetWindowPos = lambda *a: None
    win32gui.GetWindowPlacement = lambda *a: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))
    win32gui.GetWindowRect = lambda *a: (0, 0, 800, 600)
    win32gui.EnumWindows = lambda callback, extra: None
    monkeypatch.setitem(sys.modules, "win32gui", win32gui)
    monkeypatch.setitem(sys.modules, "win32con", win32con)


def _layout():
    return {
        "name": "L1",
        "windows": [{
            "exe_path": "C:\\app.exe",
            "title_snapshot": "App - foo",
            "title_pattern": "foo$",
            "class_name": "C1",
            "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600],
                          "min_pos": [-1, -1], "max_pos": [-1, -1]},
            "z_order": 0,
        }],
        "monitors": [],
    }


def test_rollback_fast_mode_skips_ensure_apps_running(monkeypatch, tmp_path):
    """mode='fast'면 ensure_apps_running이 호출되지 않아야 한다."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [{
        "hwnd": 0xABCD, "exe_path": "C:\\app.exe",
        "title_snapshot": "App - foo", "class_name": "C1", "is_hidden": False,
    }])

    ensure_called = {"n": 0}
    def fake_ensure(*a, **kw):
        ensure_called["n"] += 1
        return 0
    monkeypatch.setattr("src.launcher.ensure_apps_running", fake_ensure)

    # Bypass logging setup file IO
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert ensure_called["n"] == 0, "fast mode인데 ensure_apps_running이 호출됨"


def test_rollback_full_mode_calls_ensure_apps_running(monkeypatch, tmp_path):
    """mode='full'이면 ensure_apps_running이 호출되어야 한다(현행 동작)."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "full"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])

    scan_count = {"n": 0}
    def fake_list_current():
        scan_count["n"] += 1
        return [{"hwnd": 0xABCD, "exe_path": "C:\\app.exe",
                 "title_snapshot": "App - foo", "class_name": "C1", "is_hidden": False}]
    monkeypatch.setattr("src.capture.list_current_windows", fake_list_current)

    ensure_called = {"n": 0}
    def fake_ensure(*a, **kw):
        ensure_called["n"] += 1
        return 0
    monkeypatch.setattr("src.launcher.ensure_apps_running", fake_ensure)
    monkeypatch.setattr("time.sleep", lambda *_: None)

    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])
    try:
        rollback.main()
    except SystemExit:
        pass

    assert ensure_called["n"] == 1, "full mode인데 ensure_apps_running이 호출되지 않음"


def test_rollback_calls_sys_exit_zero_on_completion(monkeypatch, tmp_path):
    """정상 완료 시 sys.exit(0)이 호출되어야 한다(콘솔창 즉시 종료 보장)."""
    _stub_win32(monkeypatch)

    monkeypatch.setattr("src.storage.load_config", lambda: {
        "auto_rollback": {"layout_name": "L1", "mode": "fast"},
    })
    monkeypatch.setattr("src.storage.load_layout", lambda name: _layout())
    monkeypatch.setattr("src.monitors.list_current_monitors", lambda: [])
    monkeypatch.setattr("src.capture.list_current_windows", lambda: [])
    monkeypatch.setattr("src.paths.APPDATA", tmp_path)

    sys.modules.pop("cli.rollback", None)
    from cli import rollback
    monkeypatch.setattr(sys, "argv", ["rollback.py"])

    import pytest as _pt
    with _pt.raises(SystemExit) as exc:
        rollback.main()
    assert exc.value.code == 0
