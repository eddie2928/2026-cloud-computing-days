"""Tests for restore.py matching and placement logic."""
import sys
import types
import pytest


@pytest.fixture(autouse=True)
def mock_win32(monkeypatch):
    """Create mock win32 modules so tests run without pywin32 installed."""
    win32gui = types.ModuleType("win32gui")
    win32con = types.ModuleType("win32con")

    win32con.SW_SHOWNORMAL = 1
    win32con.SW_SHOWMINIMIZED = 2
    win32con.SW_SHOWMAXIMIZED = 3

    sys.modules["win32gui"] = win32gui
    sys.modules["win32con"] = win32con
    yield
    for mod in ["win32gui", "win32con"]:
        sys.modules.pop(mod, None)
    sys.modules.pop("src.restore", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _saved(exe="C:\\app.exe", title_pattern="", class_name="AppClass"):
    return {
        "exe_path": exe,
        "title_pattern": title_pattern,
        "class_name": class_name,
        "title_snapshot": "App Window",
        "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]},
        "z_order": 0,
    }


def _running(hwnd=1, exe="C:\\app.exe", title="App Window", class_name="AppClass"):
    return {
        "hwnd": hwnd,
        "exe_path": exe,
        "title_snapshot": title,
        "class_name": class_name,
    }


# ---------------------------------------------------------------------------
# score_window tests
# ---------------------------------------------------------------------------

def test_match_by_exe_only():
    from src.restore import score_window
    saved = _saved(exe="C:\\app.exe", title_pattern="", class_name="OtherClass")
    running = _running(hwnd=1, exe="C:\\app.exe", title="App Window", class_name="AppClass")
    # exe matches (+10), no title pattern, class doesn't match
    assert score_window(saved, running, set()) == 10


def test_match_by_exe_and_title():
    from src.restore import score_window
    saved = _saved(exe="C:\\app.exe", title_pattern="App.*", class_name="OtherClass")
    running = _running(hwnd=1, exe="C:\\app.exe", title="App Window", class_name="AppClass")
    # exe (+10) + title (+5) = 15
    assert score_window(saved, running, set()) == 15


def test_match_by_exe_title_class():
    from src.restore import score_window
    saved = _saved(exe="C:\\app.exe", title_pattern="App.*", class_name="AppClass")
    running = _running(hwnd=1, exe="C:\\app.exe", title="App Window", class_name="AppClass")
    # exe (+10) + title (+5) + class (+3) = 18
    assert score_window(saved, running, set()) == 18


def test_no_match_score_zero():
    from src.restore import score_window
    saved = _saved(exe="C:\\notepad.exe", title_pattern="Notepad", class_name="Notepad")
    running = _running(hwnd=1, exe="C:\\chrome.exe", title="Google Chrome", class_name="Chrome_WidgetWin_1")
    # nothing matches, score = 0
    assert score_window(saved, running, set()) == 0


def test_duplicate_prevention():
    from src.restore import score_window
    saved = _saved(exe="C:\\app.exe")
    running = _running(hwnd=42, exe="C:\\app.exe")
    already_assigned = {42}
    assert score_window(saved, running, already_assigned) == -100


def test_match_ambiguous_prefers_highest_score():
    from src.restore import match_windows
    saved = [_saved(exe="C:\\app.exe", title_pattern="App.*", class_name="AppClass")]
    # running1 matches exe+title+class (score=18), running2 matches exe only (score=10)
    running1 = _running(hwnd=10, exe="C:\\app.exe", title="App Window", class_name="AppClass")
    running2 = _running(hwnd=20, exe="C:\\app.exe", title="Other Title", class_name="OtherClass")
    results = match_windows(saved, [running1, running2])
    assert len(results) == 1
    matched_hwnd = results[0][1]["hwnd"]
    assert matched_hwnd == 10  # higher score wins


def test_empty_title_pattern_skips_title_scoring():
    from src.restore import score_window
    saved = _saved(exe="C:\\app.exe", title_pattern="", class_name="OtherClass")
    running = _running(hwnd=1, exe="C:\\app.exe", title="Anything Goes Here")
    # title_pattern is "", so no title score; exe only = 10
    assert score_window(saved, running, set()) == 10


# ---------------------------------------------------------------------------
# match_windows tests
# ---------------------------------------------------------------------------

def test_match_returns_none_when_no_candidate():
    from src.restore import match_windows
    # saved has class "MissingClass", running has class "OtherClass" — nothing matches
    saved = [_saved(exe="C:\\missing.exe", class_name="MissingClass")]
    running = [_running(hwnd=1, exe="C:\\other.exe", class_name="OtherClass")]
    results = match_windows(saved, running)
    assert len(results) == 1
    assert results[0][1] is None


def test_duplicate_prevention_second_gets_no_match():
    from src.restore import match_windows
    # Two saved windows want the same running window
    saved1 = _saved(exe="C:\\app.exe", title_pattern="App.*", class_name="AppClass")
    saved2 = _saved(exe="C:\\app.exe", title_pattern="App.*", class_name="AppClass")
    running = [_running(hwnd=1, exe="C:\\app.exe", title="App Window", class_name="AppClass")]
    results = match_windows([saved1, saved2], running)
    assert results[0][1] is not None       # first saved gets matched
    assert results[1][1] is None           # second saved gets nothing (duplicate penalty)


# ---------------------------------------------------------------------------
# restore_placement tests
# ---------------------------------------------------------------------------

def test_restore_placement_normal(monkeypatch):
    import win32gui, win32con
    calls = {}

    def mock_set_placement(hwnd, placement_tuple):
        calls["hwnd"] = hwnd
        calls["placement"] = placement_tuple

    win32gui.SetWindowPlacement = mock_set_placement

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": [10, 20, 810, 620], "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(100, placement)

    assert result is True
    assert calls["hwnd"] == 100
    assert calls["placement"][1] == win32con.SW_SHOWNORMAL
    assert calls["placement"][4] == (10, 20, 810, 620)


def test_restore_placement_maximized(monkeypatch):
    import win32gui, win32con
    calls = {}

    def mock_set_placement(hwnd, placement_tuple):
        calls["placement"] = placement_tuple

    win32gui.SetWindowPlacement = mock_set_placement

    from src.restore import restore_placement
    placement = {"state": "maximized", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(200, placement)

    assert result is True
    assert calls["placement"][1] == win32con.SW_SHOWMAXIMIZED


def test_restore_placement_minimized(monkeypatch):
    import win32gui, win32con
    calls = {}

    def mock_set_placement(hwnd, placement_tuple):
        calls["placement"] = placement_tuple

    win32gui.SetWindowPlacement = mock_set_placement

    from src.restore import restore_placement
    placement = {"state": "minimized", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(300, placement)

    assert result is True
    assert calls["placement"][1] == win32con.SW_SHOWMINIMIZED


def test_restore_placement_returns_false_on_exception(monkeypatch):
    import win32gui

    def mock_set_placement(hwnd, placement_tuple):
        raise OSError("access denied")

    win32gui.SetWindowPlacement = mock_set_placement

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(999, placement)
    assert result is False
