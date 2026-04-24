import sys
import types
import pytest


@pytest.fixture(autouse=True)
def mock_win32(monkeypatch):
    """Create mock win32 modules so tests run without pywin32 installed."""
    win32gui = types.ModuleType("win32gui")
    win32process = types.ModuleType("win32process")
    win32con = types.ModuleType("win32con")
    win32api = types.ModuleType("win32api")
    pywintypes = types.ModuleType("pywintypes")

    win32con.WS_EX_TOOLWINDOW = 0x80
    win32con.GW_HWNDNEXT = 2
    win32con.SW_SHOWNORMAL = 1
    win32con.SW_SHOWMINIMIZED = 2
    win32con.SW_SHOWMAXIMIZED = 3
    win32con.GWL_EXSTYLE = -20

    sys.modules["win32gui"] = win32gui
    sys.modules["win32process"] = win32process
    sys.modules["win32con"] = win32con
    sys.modules["win32api"] = win32api
    sys.modules["pywintypes"] = pywintypes
    yield
    for mod in ["win32gui", "win32process", "win32con", "win32api", "pywintypes"]:
        sys.modules.pop(mod, None)
    sys.modules.pop("src.capture", None)



def test_filters_empty_title(monkeypatch):
    import win32gui, win32con
    win32gui.EnumWindows = lambda cb, extra: cb(1, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: ""  # empty title
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\prog.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert results == []


def test_filters_invisible_windows(monkeypatch):
    import win32gui, win32con
    win32gui.EnumWindows = lambda cb, extra: cb(2, extra)
    win32gui.IsWindowVisible = lambda h: False  # invisible
    win32gui.GetWindowText = lambda h: "Some Window"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\prog.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert results == []


def test_filters_tool_windows(monkeypatch):
    import win32gui, win32con
    hwnd = 3
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Tool Window"
    win32gui.GetWindowLong = lambda h, flag: win32con.WS_EX_TOOLWINDOW  # tool window
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\prog.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert results == []


def test_returns_expected_keys(monkeypatch):
    import win32gui, win32con
    hwnd = 4
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Notepad"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "Notepad"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWNORMAL, (-1, -1), (-1, -1), (100, 100, 900, 700))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\Windows\\notepad.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    w = results[0]
    expected_keys = {
        "exe_path", "exe_args", "cwd", "title_snapshot", "title_pattern",
        "class_name", "placement", "monitor_index", "z_order",
        "is_topmost", "is_uwp", "hwnd"
    }
    assert set(w.keys()) == expected_keys


def test_placement_has_expected_subkeys(monkeypatch):
    import win32gui, win32con
    hwnd = 5
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Chrome"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "Chrome_WidgetWin_1"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWNORMAL, (-1, -1), (-1, -1), (0, 0, 1920, 1080))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\Program Files\\Google\\Chrome\\chrome.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    p = results[0]["placement"]
    assert "state" in p
    assert "normal_rect" in p
    assert "min_pos" in p
    assert "max_pos" in p


def test_uwp_window_is_flagged(monkeypatch):
    import win32gui, win32con
    hwnd = 6
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Calculator"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "ApplicationFrameWindow"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWNORMAL, (-1, -1), (-1, -1), (0, 0, 400, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\Windows\\SystemApps\\ApplicationFrameHost.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["is_uwp"] is True


def test_non_uwp_window_not_flagged(monkeypatch):
    import win32gui, win32con
    hwnd = 7
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Notepad"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "Notepad"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWNORMAL, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\Windows\\notepad.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["is_uwp"] is False


def test_minimized_state(monkeypatch):
    import win32gui, win32con
    hwnd = 8
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Minimized App"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWMINIMIZED, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\app.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["placement"]["state"] == "minimized"


def test_maximized_state(monkeypatch):
    import win32gui, win32con
    hwnd = 9
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Maximized App"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, win32con.SW_SHOWMAXIMIZED, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\app.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: False)

    results = cap.list_current_windows()
    assert len(results) == 1
    assert results[0]["placement"]["state"] == "maximized"


def test_filters_cloaked_windows(monkeypatch):
    import win32gui, win32con
    hwnd = 10
    win32gui.EnumWindows = lambda cb, extra: cb(hwnd, extra)
    win32gui.IsWindowVisible = lambda h: True
    win32gui.GetWindowText = lambda h: "Cloaked Window"
    win32gui.GetWindowLong = lambda h, flag: 0
    win32gui.GetClassName = lambda h: "SomeClass"
    win32gui.GetWindowPlacement = lambda h: (0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600))

    import src.capture as cap
    monkeypatch.setattr(cap, "_get_exe_path", lambda h: "C:\\app.exe")
    monkeypatch.setattr(cap, "_is_cloaked", lambda h: True)  # cloaked

    results = cap.list_current_windows()
    assert results == []
