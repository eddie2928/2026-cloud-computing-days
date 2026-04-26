"""Integration tests — real Windows API, no mocks.
Run with: pytest -m integration tests/integration/
These tests require a desktop environment with pywin32 installed.
"""
import logging
import subprocess
import time

import pytest

from src.capture import list_current_windows
from src.restore import restore_layout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_exe_window(exe_name: str, timeout: float = 15.0) -> dict | None:
    """Poll until a window from exe_name appears; return window dict or None."""
    deadline = time.monotonic() + timeout
    exe_lower = exe_name.lower()
    while time.monotonic() < deadline:
        for w in list_current_windows():
            if exe_lower in w.get("exe_path", "").lower():
                return w
        time.sleep(0.5)
    return None


def _kill_all(exe_name: str) -> None:
    subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True)
    time.sleep(1.5)


def _rects_close(r1: list, r2: list, tol: int = 20) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(r1, r2))


def chrome_installed() -> bool:
    import os
    return os.path.exists(
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )


# ---------------------------------------------------------------------------
# ITC1: Notepad 창 저장 → 위치 이동 → 복구 → 위치 검증
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc1_notepad_restore_position():
    """Save notepad position, move it, restore and verify position matches."""
    import win32gui
    import win32con

    proc = subprocess.Popen(["notepad.exe"])
    try:
        w = _wait_for_exe_window("notepad.exe")
        assert w is not None, "Notepad window did not appear"
        hwnd = w["hwnd"]

        original_rect = w["placement"]["normal_rect"]  # [x, y, w, h]

        # Build minimal layout
        layout = {
            "name": "itc1",
            "windows": [w],
            "monitors": [],
        }

        # Move window to a different position
        x2, y2 = original_rect[0] + 200, original_rect[1] + 150
        win32gui.SetWindowPos(hwnd, None, x2, y2, original_rect[2], original_rect[3],
                              0x0010 | 0x0004)  # SWP_NOACTIVATE | SWP_NOZORDER

        # Restore
        running = list_current_windows()
        result = restore_layout(layout, running_windows=running)
        assert result["restored"] == 1

        # Verify position
        placement = win32gui.GetWindowPlacement(hwnd)
        rc = placement[4]  # LTRB
        actual = [rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1]]
        assert _rects_close(actual, original_rect), f"Expected ~{original_rect}, got {actual}"
    finally:
        proc.terminate()
        _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC2: Notepad 2개 창 저장 → 복구 → 각각 위치 검증
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc2_two_notepad_windows_restore():
    """Two notepad windows: save, move both, restore, verify each."""
    import win32gui

    proc1 = subprocess.Popen(["notepad.exe"])
    w1 = _wait_for_exe_window("notepad.exe")
    assert w1 is not None

    proc2 = subprocess.Popen(["notepad.exe"])
    # Wait for second window (hwnd different from first)
    deadline = time.monotonic() + 15.0
    w2 = None
    while time.monotonic() < deadline:
        for w in list_current_windows():
            if "notepad.exe" in w.get("exe_path", "").lower() and w["hwnd"] != w1["hwnd"]:
                w2 = w
                break
        if w2:
            break
        time.sleep(0.5)

    try:
        assert w2 is not None, "Second Notepad window did not appear"

        layout = {"name": "itc2", "windows": [w1, w2], "monitors": []}
        orig1 = w1["placement"]["normal_rect"]
        orig2 = w2["placement"]["normal_rect"]

        # Move both windows
        for hwnd, rect in [(w1["hwnd"], orig1), (w2["hwnd"], orig2)]:
            win32gui.SetWindowPos(hwnd, None, rect[0] + 300, rect[1] + 100,
                                  rect[2], rect[3], 0x0010 | 0x0004)

        running = list_current_windows()
        result = restore_layout(layout, running_windows=running)
        assert result["restored"] == 2

        # Both windows have identical titles so matching is ambiguous.
        # Verify that each hwnd ended up at one of the two original positions
        # (the restore may swap which window gets which saved slot).
        expected_positions = [orig1, orig2]
        for hwnd in [w1["hwnd"], w2["hwnd"]]:
            placement = win32gui.GetWindowPlacement(hwnd)
            rc = placement[4]
            actual = [rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1]]
            matched = any(_rects_close(actual, exp) for exp in expected_positions)
            assert matched, f"hwnd=0x{hwnd:x}: actual {actual} doesn't match either of {expected_positions}"
    finally:
        proc1.terminate()
        proc2.terminate()
        _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC3: Chrome 완전 종료 후 복구 → Chrome 창 존재 확인
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not chrome_installed(), reason="Chrome not installed")
def test_itc3_chrome_killed_and_restored(caplog):
    """Kill Chrome entirely, restore layout, verify Chrome window appears."""
    CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    _kill_all("chrome.exe")
    proc = subprocess.Popen([CHROME_EXE, "--new-window"])
    w = _wait_for_exe_window("chrome.exe", timeout=15)
    assert w is not None, "Chrome window did not appear after launch"

    layout = {"name": "itc3", "windows": [w], "monitors": []}

    # Kill Chrome completely
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)

    with caplog.at_level(logging.WARNING, logger="restore"):
        result = restore_layout(layout)

    time.sleep(5)
    windows_after = list_current_windows()
    chrome_windows = [x for x in windows_after if "chrome.exe" in x.get("exe_path", "").lower()]
    assert len(chrome_windows) >= 1, "Chrome window not found after restore"

    chrome_win = chrome_windows[0]
    actual_rect = chrome_win["placement"]["normal_rect"]
    saved_rect  = w["placement"]["normal_rect"]
    assert _rects_close(actual_rect, saved_rect, tol=30), \
        f"ITC3: position mismatch — saved={saved_rect}, actual={actual_rect}"

    no_candidate_warns = [r for r in caplog.records if "no candidate" in r.message]
    assert no_candidate_warns == [], f"Unexpected 'no candidate' warnings: {no_candidate_warns}"

    _kill_all("chrome.exe")


# ---------------------------------------------------------------------------
# ITC4: Chrome 창만 닫기 (프로세스 유지) → 복구 → Chrome 창 존재 확인
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not chrome_installed(), reason="Chrome not installed")
def test_itc4_chrome_background_only_then_restored(caplog):
    """Core bug scenario: Chrome process alive but no window → restore creates window."""
    import win32gui
    import win32con

    CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    WM_CLOSE = 0x0010

    _kill_all("chrome.exe")
    proc = subprocess.Popen([CHROME_EXE, "--new-window"])
    w = _wait_for_exe_window("chrome.exe", timeout=15)
    assert w is not None, "Chrome window did not appear after launch"

    layout = {"name": "itc4", "windows": [w], "monitors": []}
    hwnd = w["hwnd"]

    # Close just the window (leave background process running)
    win32gui.PostMessage(hwnd, WM_CLOSE, 0, 0)
    time.sleep(2)

    # Verify: process still alive, window gone
    import psutil
    chrome_procs = [p for p in psutil.process_iter(["name"])
                    if (p.info.get("name") or "").lower() == "chrome.exe"]
    assert len(chrome_procs) > 0, "Chrome process should still be running"

    visible = [x for x in list_current_windows() if "chrome.exe" in x.get("exe_path", "").lower()]
    # If Chrome auto-recreated a window, skip the "no visible window" check
    if visible:
        pytest.skip("Chrome auto-recreated window; background-only state not achievable in this env")

    with caplog.at_level(logging.WARNING, logger="restore"):
        result = restore_layout(layout)

    time.sleep(5)
    windows_after = list_current_windows()
    chrome_windows = [x for x in windows_after if "chrome.exe" in x.get("exe_path", "").lower()]
    assert len(chrome_windows) >= 1, "Chrome window not found after restore"

    chrome_win = chrome_windows[0]
    actual_rect = chrome_win["placement"]["normal_rect"]
    saved_rect  = w["placement"]["normal_rect"]
    assert _rects_close(actual_rect, saved_rect, tol=30), \
        f"ITC4: position mismatch — saved={saved_rect}, actual={actual_rect}"

    no_candidate_warns = [r for r in caplog.records if "no candidate" in r.message]
    assert no_candidate_warns == [], f"Unexpected 'no candidate' warnings: {no_candidate_warns}"

    _kill_all("chrome.exe")


# ---------------------------------------------------------------------------
# ITC5: Notepad 종료 후 복구 → 저장 위치로 복구 (위치 정확도 검증)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc5_notepad_killed_and_restored_position():
    """Kill Notepad, restore layout, verify it comes back at the saved position."""
    import win32gui

    proc = subprocess.Popen(["notepad.exe"])
    try:
        w = _wait_for_exe_window("notepad.exe")
        assert w is not None, "Notepad window did not appear"
        hwnd = w["hwnd"]

        target = [200, 150, 700, 500]
        win32gui.SetWindowPos(hwnd, None, target[0], target[1], target[2], target[3],
                              0x0010 | 0x0004)
        time.sleep(0.3)

        wins = list_current_windows()
        notepad_win = next((x for x in wins if "notepad.exe" in x.get("exe_path", "").lower()
                            and x["hwnd"] == hwnd), None)
        assert notepad_win is not None
        captured_rect = notepad_win["placement"]["normal_rect"]

        layout = {"name": "itc5", "windows": [notepad_win], "monitors": []}
    finally:
        proc.terminate()
        _kill_all("notepad.exe")

    result = restore_layout(layout, stabilize_ms=500)
    assert result["restored"] == 1

    wins_after = list_current_windows()
    notepad_wins = [x for x in wins_after if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(notepad_wins) >= 1, "Notepad window not found after restore"

    actual_rect = notepad_wins[0]["placement"]["normal_rect"]
    assert _rects_close(actual_rect, captured_rect, tol=20), \
        f"ITC5: position mismatch — saved={captured_rect}, actual={actual_rect}"

    _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC6: Notepad 최대화 상태 종료 후 복구 → 최대화 상태 재현
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc6_notepad_maximized_killed_and_restored():
    """Kill maximized Notepad, restore and verify it comes back maximized."""
    import win32gui
    import win32con

    proc = subprocess.Popen(["notepad.exe"])
    try:
        w = _wait_for_exe_window("notepad.exe")
        assert w is not None, "Notepad window did not appear"
        hwnd = w["hwnd"]

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        time.sleep(0.3)

        wins = list_current_windows()
        notepad_win = next((x for x in wins if "notepad.exe" in x.get("exe_path", "").lower()
                            and x["hwnd"] == hwnd), None)
        assert notepad_win is not None
        assert notepad_win["placement"]["state"] == "maximized", "Window should be maximized"

        layout = {"name": "itc6", "windows": [notepad_win], "monitors": []}
    finally:
        proc.terminate()
        _kill_all("notepad.exe")

    result = restore_layout(layout, stabilize_ms=500)
    assert result["restored"] == 1

    wins_after = list_current_windows()
    notepad_wins = [x for x in wins_after if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(notepad_wins) >= 1, "Notepad window not found after restore"

    restored_hwnd = notepad_wins[0]["hwnd"]
    placement = win32gui.GetWindowPlacement(restored_hwnd)
    assert placement[1] == win32con.SW_SHOWMAXIMIZED, \
        f"ITC6: expected maximized (showCmd={win32con.SW_SHOWMAXIMIZED}), got {placement[1]}"

    _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC7: Notepad 2창 종료 후 복구 → 각 창이 저장된 위치 중 하나와 일치
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc7_two_notepad_windows_killed_and_restored():
    """Kill two Notepad windows, restore, verify each appears at one of the saved positions."""
    import win32gui

    proc1 = subprocess.Popen(["notepad.exe"])
    w1 = _wait_for_exe_window("notepad.exe")
    assert w1 is not None

    proc2 = subprocess.Popen(["notepad.exe"])
    deadline = time.monotonic() + 15.0
    w2 = None
    while time.monotonic() < deadline:
        for w in list_current_windows():
            if "notepad.exe" in w.get("exe_path", "").lower() and w["hwnd"] != w1["hwnd"]:
                w2 = w
                break
        if w2:
            break
        time.sleep(0.5)

    try:
        assert w2 is not None, "Second Notepad window did not appear"

        pos1 = [100, 100, 600, 400]
        pos2 = [750, 300, 600, 400]
        win32gui.SetWindowPos(w1["hwnd"], None, pos1[0], pos1[1], pos1[2], pos1[3], 0x0010 | 0x0004)
        win32gui.SetWindowPos(w2["hwnd"], None, pos2[0], pos2[1], pos2[2], pos2[3], 0x0010 | 0x0004)
        time.sleep(0.3)

        wins = list_current_windows()
        notepad_wins = [x for x in wins if "notepad.exe" in x.get("exe_path", "").lower()]
        assert len(notepad_wins) == 2
        layout = {"name": "itc7", "windows": notepad_wins, "monitors": []}
        expected_positions = [pos1, pos2]
    finally:
        proc1.terminate()
        proc2.terminate()
        _kill_all("notepad.exe")

    result = restore_layout(layout, stabilize_ms=500)
    assert result["restored"] == 2

    wins_after = list_current_windows()
    notepad_wins_after = [x for x in wins_after if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(notepad_wins_after) == 2, "Expected 2 Notepad windows after restore"

    for win in notepad_wins_after:
        actual = win["placement"]["normal_rect"]
        matched = any(_rects_close(actual, exp, tol=20) for exp in expected_positions)
        assert matched, f"ITC7: hwnd=0x{win['hwnd']:x} actual={actual} doesn't match either of {expected_positions}"

    _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC8: Notepad 화면 모서리(x=5,y=5) 위치 종료 후 복구
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc8_notepad_corner_position_restored():
    """Kill Notepad at near-corner position (5,5), restore and verify same position."""
    import win32gui

    proc = subprocess.Popen(["notepad.exe"])
    try:
        w = _wait_for_exe_window("notepad.exe")
        assert w is not None, "Notepad window did not appear"
        hwnd = w["hwnd"]

        target = [5, 5, 500, 400]
        win32gui.SetWindowPos(hwnd, None, target[0], target[1], target[2], target[3],
                              0x0010 | 0x0004)
        time.sleep(0.3)

        wins = list_current_windows()
        notepad_win = next((x for x in wins if "notepad.exe" in x.get("exe_path", "").lower()
                            and x["hwnd"] == hwnd), None)
        assert notepad_win is not None
        captured_rect = notepad_win["placement"]["normal_rect"]

        layout = {"name": "itc8", "windows": [notepad_win], "monitors": []}
    finally:
        proc.terminate()
        _kill_all("notepad.exe")

    result = restore_layout(layout, stabilize_ms=500)
    assert result["restored"] == 1

    wins_after = list_current_windows()
    notepad_wins = [x for x in wins_after if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(notepad_wins) >= 1, "Notepad window not found after restore"

    actual_rect = notepad_wins[0]["placement"]["normal_rect"]
    assert _rects_close(actual_rect, target, tol=20), \
        f"ITC8: position mismatch — expected={target}, actual={actual_rect}"

    _kill_all("notepad.exe")


# ---------------------------------------------------------------------------
# ITC9: 동일 레이아웃 연속 2회 복구 — 멱등성(idempotency) 검증
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_itc9_restore_idempotent_two_runs():
    """Restore the same layout twice; both runs should place Notepad at the saved position."""
    import win32gui

    proc = subprocess.Popen(["notepad.exe"])
    try:
        w = _wait_for_exe_window("notepad.exe")
        assert w is not None, "Notepad window did not appear"
        hwnd = w["hwnd"]

        target = [200, 200, 700, 500]
        win32gui.SetWindowPos(hwnd, None, target[0], target[1], target[2], target[3],
                              0x0010 | 0x0004)
        time.sleep(0.3)

        wins = list_current_windows()
        notepad_win = next((x for x in wins if "notepad.exe" in x.get("exe_path", "").lower()
                            and x["hwnd"] == hwnd), None)
        assert notepad_win is not None
        captured_rect = notepad_win["placement"]["normal_rect"]

        layout = {"name": "itc9", "windows": [notepad_win], "monitors": []}
    finally:
        proc.terminate()
        _kill_all("notepad.exe")

    # 1차 복구
    result1 = restore_layout(layout, stabilize_ms=500)
    assert result1["restored"] == 1

    wins1 = list_current_windows()
    np1 = [x for x in wins1 if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(np1) >= 1
    actual1 = np1[0]["placement"]["normal_rect"]
    assert _rects_close(actual1, captured_rect, tol=20), \
        f"ITC9 run1: position mismatch — saved={captured_rect}, actual={actual1}"

    _kill_all("notepad.exe")

    # 2차 복구
    result2 = restore_layout(layout, stabilize_ms=500)
    assert result2["restored"] == 1

    wins2 = list_current_windows()
    np2 = [x for x in wins2 if "notepad.exe" in x.get("exe_path", "").lower()]
    assert len(np2) >= 1
    actual2 = np2[0]["placement"]["normal_rect"]
    assert _rects_close(actual2, captured_rect, tol=20), \
        f"ITC9 run2: position mismatch — saved={captured_rect}, actual={actual2}"

    _kill_all("notepad.exe")
