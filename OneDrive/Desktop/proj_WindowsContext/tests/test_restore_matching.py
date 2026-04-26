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

    win32gui.SetWindowPos = lambda *a: None
    win32gui.GetWindowPlacement = lambda *a: None  # default: verification fails gracefully

    sys.modules["win32gui"] = win32gui
    sys.modules["win32con"] = win32con
    yield
    for mod in ["win32gui", "win32con"]:
        sys.modules.pop(mod, None)
    sys.modules.pop("src.restore", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _saved(exe_path="C:\\app.exe", title_pattern="", class_name="AppClass",
           title_snapshot="App Window"):
    return {
        "exe_path": exe_path,
        "title_pattern": title_pattern,
        "class_name": class_name,
        "title_snapshot": title_snapshot,
        "placement": {"state": "normal", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]},
        "z_order": 0,
    }


def _running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="App Window", class_name="AppClass"):
    return {
        "hwnd": hwnd,
        "exe_path": exe_path,
        "title_snapshot": title_snapshot,
        "class_name": class_name,
    }


# ---------------------------------------------------------------------------
# score_window tests
# ---------------------------------------------------------------------------

def test_match_by_exe_only():
    from src.restore import score_window
    saved = _saved(exe_path="C:\\app.exe", title_pattern="", class_name="OtherClass")
    running = _running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="Different Window", class_name="AppClass")
    # exe matches (+10), no title pattern, title_snapshot differs, class doesn't match
    assert score_window(saved, running, set()) == 10


def test_match_by_exe_and_title():
    from src.restore import score_window
    # saved snapshot differs from running → only pattern bonus fires (not snapshot bonus)
    saved = _saved(exe_path="C:\\app.exe", title_pattern="App.*", class_name="OtherClass",
                   title_snapshot="Old Title")
    running = _running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="App Window", class_name="AppClass")
    # exe (+10) + pattern (+5) = 15
    assert score_window(saved, running, set()) == 15


def test_match_by_exe_title_class():
    from src.restore import score_window
    # saved snapshot differs from running → pattern + class only
    saved = _saved(exe_path="C:\\app.exe", title_pattern="App.*", class_name="AppClass",
                   title_snapshot="Old Title")
    running = _running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="App Window", class_name="AppClass")
    # exe (+10) + pattern (+5) + class (+3) = 18
    assert score_window(saved, running, set()) == 18


def test_no_match_score_zero():
    from src.restore import score_window
    saved = _saved(exe_path="C:\\notepad.exe", title_pattern="Notepad", class_name="Notepad")
    running = _running(hwnd=1, exe_path="C:\\chrome.exe", title_snapshot="Google Chrome", class_name="Chrome_WidgetWin_1")
    # nothing matches, score = 0
    assert score_window(saved, running, set()) == 0


def test_duplicate_prevention():
    from src.restore import score_window
    saved = _saved(exe_path="C:\\app.exe")
    running = _running(hwnd=42, exe_path="C:\\app.exe")
    already_assigned = {42}
    assert score_window(saved, running, already_assigned) == -100


def test_match_ambiguous_prefers_highest_score():
    from src.restore import match_windows
    saved = [_saved(exe_path="C:\\app.exe", title_pattern="App.*", class_name="AppClass")]
    # running1 matches exe+title+class (score=18), running2 matches exe only (score=10)
    running1 = _running(hwnd=10, exe_path="C:\\app.exe", title_snapshot="App Window", class_name="AppClass")
    running2 = _running(hwnd=20, exe_path="C:\\app.exe", title_snapshot="Other Title", class_name="OtherClass")
    results = match_windows(saved, [running1, running2])
    assert len(results) == 1
    matched_hwnd = results[0][1]["hwnd"]
    assert matched_hwnd == 10  # higher score wins


def test_empty_title_pattern_skips_title_scoring():
    from src.restore import score_window
    saved = _saved(exe_path="C:\\app.exe", title_pattern="", class_name="OtherClass",
                   title_snapshot="App Window")
    running = _running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="Anything Goes Here")
    # title_pattern is "" and title_snapshot differs, so no title score; exe only = 10
    assert score_window(saved, running, set()) == 10


# ---------------------------------------------------------------------------
# match_windows tests
# ---------------------------------------------------------------------------

def test_match_returns_none_when_no_candidate():
    from src.restore import match_windows
    # exe, class, title_snapshot all differ — nothing matches, score stays 0
    saved = [_saved(exe_path="C:\\missing.exe", class_name="MissingClass",
                    title_snapshot="Missing App")]
    running = [_running(hwnd=1, exe_path="C:\\other.exe", class_name="OtherClass",
                        title_snapshot="Other App")]
    results = match_windows(saved, running)
    assert len(results) == 1
    assert results[0][1] is None


def test_duplicate_prevention_second_gets_no_match():
    from src.restore import match_windows
    # Two saved windows want the same running window
    saved1 = _saved(exe_path="C:\\app.exe", title_pattern="App.*", class_name="AppClass")
    saved2 = _saved(exe_path="C:\\app.exe", title_pattern="App.*", class_name="AppClass")
    running = [_running(hwnd=1, exe_path="C:\\app.exe", title_snapshot="App Window", class_name="AppClass")]
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

    nr = [10, 20, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
    win32gui.SetWindowPlacement = mock_set_placement
    win32gui.GetWindowPlacement = lambda hwnd: (0, 1, (-1, -1), (-1, -1), correct_ltrb)

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(100, placement)

    assert result is True
    assert calls["hwnd"] == 100
    assert calls["placement"][1] == win32con.SW_SHOWNORMAL
    assert calls["placement"][4] == (10, 20, 810, 620)  # XYWH converted back to LTRB


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


# ---------------------------------------------------------------------------
# score_window: title_snapshot exact match bonus
# ---------------------------------------------------------------------------

def test_exact_title_snapshot_match_scores_5_when_no_pattern():
    from src.restore import score_window
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="My Window", title_pattern="")
    running = _running(exe_path="C:\\app.exe", title_snapshot="My Window", class_name="OtherClass")
    assert score_window(saved, running, set()) == 15  # exe(10) + snapshot_exact(5)


def test_no_bonus_when_title_snapshot_differs():
    from src.restore import score_window
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="Window A", title_pattern="")
    running = _running(exe_path="C:\\app.exe", title_snapshot="Window B", class_name="OtherClass")
    assert score_window(saved, running, set()) == 10  # exe(10) only


def test_pattern_and_snapshot_bonuses_stack():
    """pattern 매칭 AND snapshot 완전 일치 시 두 보너스가 모두 적용돼야 한다."""
    from src.restore import score_window
    saved  = _saved(exe_path="C:\\app.exe", title_snapshot="Window A", title_pattern="Window")
    running = _running(exe_path="C:\\app.exe", title_snapshot="Window A", class_name="OtherClass")
    assert score_window(saved, running, set()) == 20  # exe(10) + pattern(5) + snapshot(5)


def test_two_same_exe_windows_match_by_title():
    from src.restore import match_windows
    saved_a = _saved(exe_path="C:\\app.exe", title_snapshot="Doc A")
    saved_b = _saved(exe_path="C:\\app.exe", title_snapshot="Doc B")
    running_a = _running(exe_path="C:\\app.exe", title_snapshot="Doc A", hwnd=1)
    running_b = _running(exe_path="C:\\app.exe", title_snapshot="Doc B", hwnd=2)
    results = match_windows([saved_a, saved_b], [running_a, running_b])
    matched_hwnds = {r["hwnd"] for _, r in results if r}
    assert matched_hwnds == {1, 2}
    assert results[0][1]["hwnd"] == 1
    assert results[1][1]["hwnd"] == 2


def test_chrome_windows_disambiguated_when_running_order_reversed():
    """같은 title_pattern을 가진 Chrome 창 2개가 running 순서 무관하게 정확히 매칭돼야 한다."""
    from src.restore import match_windows
    saved_gmail = _saved(exe_path="C:\\chrome.exe",
                         title_snapshot="Gmail - Google Chrome",
                         title_pattern="Google\\ Chrome$")
    saved_yt = _saved(exe_path="C:\\chrome.exe",
                      title_snapshot="YouTube - Google Chrome",
                      title_pattern="Google\\ Chrome$")
    # running 순서가 저장 순서와 반대
    running_yt   = _running(exe_path="C:\\chrome.exe",
                            title_snapshot="YouTube - Google Chrome", hwnd=2)
    running_gmail = _running(exe_path="C:\\chrome.exe",
                             title_snapshot="Gmail - Google Chrome", hwnd=1)

    results = match_windows([saved_gmail, saved_yt], [running_yt, running_gmail])
    assert results[0][1]["hwnd"] == 1  # saved_gmail → running_gmail
    assert results[1][1]["hwnd"] == 2  # saved_yt   → running_yt


# ---------------------------------------------------------------------------
# restore_placement: SetWindowPos follow-up call
# ---------------------------------------------------------------------------

def test_restore_placement_normal_also_calls_set_window_pos(monkeypatch):
    from unittest.mock import MagicMock
    import win32gui, win32con
    nr = [100, 200, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock(return_value=True)
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    from src.restore import restore_placement
    placement = {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]}
    result = restore_placement(0x1234, placement)

    assert result is True
    win32gui.SetWindowPos.assert_called_once()
    args = win32gui.SetWindowPos.call_args[0]
    assert args[2] == 100  # x
    assert args[3] == 200  # y
    assert args[4] == 800  # w
    assert args[5] == 600  # h


def test_restore_placement_maximized_skips_set_window_pos(monkeypatch):
    from unittest.mock import MagicMock
    import win32gui
    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()

    from src.restore import restore_placement
    placement = {"state": "maximized", "normal_rect": [0, 0, 800, 600],
                 "min_pos": [-1, -1], "max_pos": [-1, -1]}
    restore_placement(0x1234, placement)
    win32gui.SetWindowPos.assert_not_called()


# ---------------------------------------------------------------------------
# _rects_close (UT-3a ~ UT-3f)
# ---------------------------------------------------------------------------

def test_ut3a_exact_match():
    from src.restore import _rects_close
    assert _rects_close([100, 200, 800, 600], [100, 200, 800, 600], tol=0) is True


def test_ut3b_at_tolerance_boundary():
    from src.restore import _rects_close
    assert _rects_close([100, 200, 800, 600], [110, 210, 810, 610], tol=10) is True


def test_ut3c_one_element_exceeds_tol():
    from src.restore import _rects_close
    assert _rects_close([100, 200, 800, 600], [111, 200, 800, 600], tol=10) is False


def test_ut3d_negative_coords():
    from src.restore import _rects_close
    assert _rects_close([-1920, 0, 800, 600], [-1915, 5, 795, 595], tol=10) is True
    assert _rects_close([-1920, 0, 800, 600], [-1905, 0, 800, 600], tol=10) is False


def test_ut3e_list_shorter_than_4():
    from src.restore import _rects_close
    assert _rects_close([100, 200, 800], [100, 200, 800, 600], tol=10) is False


def test_ut3f_4k_coords():
    from src.restore import _rects_close
    assert _rects_close([3840, 2160, 3840, 2160], [3842, 2162, 3838, 2158], tol=5) is True


# ---------------------------------------------------------------------------
# restore_placement retries (UT-1, UT-2, UT-5, UT-6, UT-7, UT-8, UT-9, UT-10, UT-11)
# ---------------------------------------------------------------------------

def test_ut1_second_attempt_succeeds():
    """1차 검증 실패, 2차 성공 → True, SetWindowPlacement 2회 호출."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]
    wrong_ltrb   = (0, 0, 100, 100)
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(side_effect=[
        (0, 1, (-1, -1), (-1, -1), wrong_ltrb),
        (0, 1, (-1, -1), (-1, -1), correct_ltrb),
    ])

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is True
    assert win32gui.SetWindowPlacement.call_count == 2


def test_ut2_all_retries_exhausted():
    """retries=3 모두 실패 → False, SetWindowPlacement 3회 호출."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]
    wrong_ltrb = (0, 0, 100, 100)

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), wrong_ltrb))

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is False
    assert win32gui.SetWindowPlacement.call_count == 3


def test_ut5_retries_1_fails_immediately():
    """retries=1: 단 한 번 시도 후 실패 → False, 1회만 호출."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]
    wrong_ltrb = (0, 0, 100, 100)

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), wrong_ltrb))

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=1, retry_delay_ms=0,
    )

    assert result is False
    assert win32gui.SetWindowPlacement.call_count == 1


def test_ut6_first_attempt_succeeds_no_retry():
    """첫 시도에서 즉시 성공 → True, SetWindowPlacement 1회만 호출."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is True
    assert win32gui.SetWindowPlacement.call_count == 1


def test_ut7_get_placement_short_tuple():
    """GetWindowPlacement가 len<5 반환 → crash 없이 False, retries회 호출."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0,))  # len=1

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is False
    assert win32gui.SetWindowPlacement.call_count == 3


def test_ut8_get_placement_oserror_no_crash():
    """GetWindowPlacement OSError → 예외 미전파, False 반환."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [10, 20, 800, 600]

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(side_effect=OSError("access denied"))

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is False


def test_ut9_maximized_no_get_placement_call():
    """state=maximized → GetWindowPlacement 미호출, True 반환."""
    from unittest.mock import MagicMock
    import win32gui

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock()

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "maximized", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]},
    )

    assert result is True
    win32gui.GetWindowPlacement.assert_not_called()


def test_ut10_minimized_no_get_placement_call():
    """state=minimized → GetWindowPlacement 미호출, True 반환."""
    from unittest.mock import MagicMock
    import win32gui

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock()

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "minimized", "normal_rect": [0, 0, 800, 600], "min_pos": [-1, -1], "max_pos": [-1, -1]},
    )

    assert result is True
    win32gui.GetWindowPlacement.assert_not_called()


def test_ut11_negative_coord_normal_rect():
    """음수 x 좌표(멀티모니터 왼쪽 배치) → 정상 처리, True."""
    from unittest.mock import MagicMock
    import win32gui

    nr = [-1920, 100, 800, 600]
    correct_ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])

    win32gui.SetWindowPlacement = MagicMock()
    win32gui.SetWindowPos = MagicMock()
    win32gui.GetWindowPlacement = MagicMock(return_value=(0, 1, (-1, -1), (-1, -1), correct_ltrb))

    from src.restore import restore_placement
    result = restore_placement(
        100,
        {"state": "normal", "normal_rect": nr, "min_pos": [-1, -1], "max_pos": [-1, -1]},
        retries=3, retry_delay_ms=0,
    )

    assert result is True
    args = win32gui.SetWindowPos.call_args[0]
    assert args[2] == -1920  # x


# ---------------------------------------------------------------------------
# restore_layout stabilize_ms (UT-4, UT-13, UT-14, UT-15)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_layout_deps(monkeypatch):
    """restore_layout 호출에 필요한 sys.modules 의존성을 최소한으로 모킹."""
    import types
    from unittest.mock import MagicMock
    from enum import Enum

    class MatchResult(Enum):
        FULL_MATCH = "full_match"
        PRIMARY_ONLY = "primary_only"
        NO_MATCH = "no_match"

    monitors_mod = types.ModuleType("src.monitors")
    monitors_mod.MatchResult = MatchResult
    monitors_mod.compare_monitors = lambda *a, **kw: MatchResult.FULL_MATCH
    monitors_mod.filter_to_primary = lambda windows, *a: windows
    monitors_mod.clamp_rect_to_monitor = lambda r, m: r

    launcher_mod = types.ModuleType("src.launcher")
    launcher_mod.ensure_apps_running = MagicMock()

    capture_mod = types.ModuleType("src.capture")
    capture_mod.list_current_windows = MagicMock(return_value=[])

    monkeypatch.setitem(sys.modules, "src.monitors", monitors_mod)
    monkeypatch.setitem(sys.modules, "src.launcher", launcher_mod)
    monkeypatch.setitem(sys.modules, "src.capture", capture_mod)


def test_ut4_stabilize_ms_zero_no_sleep(mock_layout_deps):
    """stabilize_ms=0 → time.sleep 미호출."""
    from unittest.mock import patch

    with patch("time.sleep") as mock_sleep:
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []}, stabilize_ms=0)

    mock_sleep.assert_not_called()


def test_ut13_stabilize_ms_500_sleeps_half_second(mock_layout_deps):
    """stabilize_ms=500 → time.sleep(0.5) 호출."""
    from unittest.mock import patch

    with patch("time.sleep") as mock_sleep:
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []}, stabilize_ms=500)

    mock_sleep.assert_called_once_with(0.5)


def test_ut14_running_windows_passed_no_sleep(mock_layout_deps):
    """running_windows를 외부에서 전달하면 stabilize_ms 무시, sleep 미호출."""
    from unittest.mock import patch

    with patch("time.sleep") as mock_sleep:
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []},
                       running_windows=[], stabilize_ms=1500)

    mock_sleep.assert_not_called()


def test_ut15_stabilize_ms_default_sleeps_1500ms(mock_layout_deps):
    """stabilize_ms 생략(기본값 1500) → time.sleep(1.5) 호출."""
    from unittest.mock import patch

    with patch("time.sleep") as mock_sleep:
        from src.restore import restore_layout
        restore_layout({"name": "t", "windows": [], "monitors": []})

    mock_sleep.assert_called_once_with(1.5)
