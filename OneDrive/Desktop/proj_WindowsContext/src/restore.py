import logging
import re
import time
from typing import Optional

logger = logging.getLogger("restore")

try:
    import pywintypes as _pywintypes
    _WIN_ERRORS = (OSError, _pywintypes.error)
except ImportError:
    _WIN_ERRORS = (OSError,)


def _rects_close(r1: list, r2: list, tol: int = 10) -> bool:
    """r1, r2 모두 [x, y, w, h] 형식. 각 요소가 tol 이내이면 True."""
    return len(r1) == 4 and len(r2) == 4 and all(abs(a - b) <= tol for a, b in zip(r1, r2))


def score_window(saved: dict, running: dict, already_assigned: set) -> int:
    """Score how well a running window matches a saved window entry."""
    if running["hwnd"] in already_assigned:
        return -100
    score = 0
    if saved.get("exe_path", "").lower() == running.get("exe_path", "").lower():
        score += 10
    pattern = saved.get("title_pattern", "")
    if pattern:
        try:
            if re.search(pattern, running.get("title_snapshot", "")):
                score += 5
        except re.error:
            pass
    if saved.get("title_snapshot") and saved["title_snapshot"] == running.get("title_snapshot"):
        score += 5
    if saved.get("class_name") and saved["class_name"] == running.get("class_name"):
        score += 3
    return score


def match_windows(saved_windows: list[dict], running_windows: list[dict]) -> list[tuple[dict, Optional[dict]]]:
    """
    For each saved window, find the best-matching running window.
    Returns list of (saved_window, matched_running_window_or_None).
    """
    assigned_hwnds: set[int] = set()
    results = []
    for saved in saved_windows:
        best_match = None
        best_score = 0
        for running in running_windows:
            s = score_window(saved, running, assigned_hwnds)
            if s > best_score:
                best_score = s
                best_match = running
        if best_match is not None:
            assigned_hwnds.add(best_match["hwnd"])
            results.append((saved, best_match))
            logger.info(
                "matched saved '%s' → hwnd=0x%x score=%d",
                saved.get("title_snapshot", saved.get("exe_path", "")),
                best_match["hwnd"],
                best_score,
            )
        else:
            results.append((saved, None))
            logger.warning(
                "no candidate for '%s' (exe=%s)",
                saved.get("title_snapshot", ""),
                saved.get("exe_path", ""),
            )
    return results


def restore_placement(hwnd: int, placement: dict, retries: int = 3, retry_delay_ms: int = 200) -> bool:
    """Apply saved placement to a window. Returns True on success."""
    try:
        import win32gui
        import win32con
    except ImportError:
        logger.error("pywin32 not installed — cannot restore placement")
        raise  # ImportError should propagate, it's a deployment error

    try:
        state = placement.get("state", "normal")
        nr = placement.get("normal_rect", [0, 0, 800, 600])  # stored as [x, y, w, h] (XYWH)
        min_pos = tuple(placement.get("min_pos", [-1, -1]))
        max_pos = tuple(placement.get("max_pos", [-1, -1]))

        if state == "minimized":
            show_cmd = win32con.SW_SHOWMINIMIZED
        elif state == "maximized":
            show_cmd = win32con.SW_SHOWMAXIMIZED
        else:
            show_cmd = win32con.SW_SHOWNORMAL

        # Convert XYWH back to LTRB for SetWindowPlacement rcNormalPosition
        ltrb = (nr[0], nr[1], nr[0] + nr[2], nr[1] + nr[3])

        SWP_NOACTIVATE     = 0x0010
        SWP_NOZORDER       = 0x0004
        SWP_NOSENDCHANGING = 0x0400  # suppress WM_WINDOWPOSCHANGING so apps (Chrome/Electron) can't override the size

        for attempt in range(1, retries + 1):
            win32gui.SetWindowPlacement(hwnd, (
                0,          # flags
                show_cmd,
                min_pos,
                max_pos,
                ltrb,       # rcNormalPosition in LTRB
            ))

            if state == "normal":
                # nr is saved as GetWindowRect (screen coords); pass SWP_NOSENDCHANGING so
                # Chrome/Electron cannot intercept WM_WINDOWPOSCHANGING and override the size.
                win32gui.SetWindowPos(
                    hwnd, None,
                    nr[0], nr[1], nr[2], nr[3],
                    SWP_NOACTIVATE | SWP_NOZORDER | SWP_NOSENDCHANGING,
                )

                # 사후 검증: GetWindowRect로 실제 화면 위치 확인 (nr은 screen coords이므로)
                try:
                    actual_ltrb = win32gui.GetWindowRect(hwnd)
                    actual_xywh = [actual_ltrb[0], actual_ltrb[1],
                                   actual_ltrb[2] - actual_ltrb[0],
                                   actual_ltrb[3] - actual_ltrb[1]]
                    if _rects_close(actual_xywh, nr, tol=10):
                        logger.info("placed hwnd=0x%x state=%s rect=%s (attempt %d)", hwnd, state, nr, attempt)
                        return True
                    logger.warning(
                        "placement verify failed hwnd=0x%x attempt=%d: wanted=%s got=%s",
                        hwnd, attempt, nr, actual_xywh,
                    )
                except OSError as e:
                    logger.warning("placement verify error hwnd=0x%x attempt=%d: %s", hwnd, attempt, e)

                if attempt < retries:
                    time.sleep(retry_delay_ms / 1000.0)
            else:
                # minimized/maximized: 상태가 목표 — SetWindowPlacement 예외 없으면 성공
                logger.info("placed hwnd=0x%x state=%s (attempt %d)", hwnd, state, attempt)
                return True

        return False
    except _WIN_ERRORS as e:
        logger.warning("failed to place hwnd=0x%x: %s", hwnd, e)
        return False


def restore_layout(
    layout: dict,
    running_windows: list[dict] = None,
    monitors_current: list[dict] = None,
    stabilize_ms: int = 1500,
    post_settle_ms: int = 2000,
    post_launch_settle_ms: int = 0,
) -> dict:
    """
    Restore a saved layout by matching saved windows to running windows
    and repositioning them.

    Args:
        layout: loaded layout dict (from storage.load_layout)
        running_windows: list of current windows (from capture.list_current_windows).
                         If None, captures current windows.
        monitors_current: current monitor list. If provided, applies monitor gate policy.
        stabilize_ms: ms to wait after launching missing apps before re-scanning.
        post_settle_ms: ms to wait after initial placement before re-applying.
                        Chrome/Electron apps process WM_WINDOWPOSCHANGED asynchronously
                        and may restore their own position 1-2 s after SetWindowPos.
                        The re-apply pass corrects this. Set to 0 to disable.

    Returns:
        {"restored": int, "failed": int, "total": int, "elapsed_ms": int}
    """
    from src.monitors import compare_monitors, filter_to_primary, clamp_rect_to_monitor, MatchResult

    t0 = time.perf_counter()
    saved_windows = layout.get("windows", [])
    saved_monitors = layout.get("monitors", [])

    logger.info("starting '%s' (%d windows)", layout.get("name", "?"), len(saved_windows))

    # Monitor gate
    if saved_monitors and monitors_current is not None:
        match = compare_monitors(saved_monitors, monitors_current)
        if match == MatchResult.PRIMARY_ONLY:
            orig_count = len(saved_windows)
            saved_windows = filter_to_primary(saved_windows, saved_monitors)
            logger.warning(
                "filtered %d windows (external monitor absent/changed) — restoring %d primary windows",
                orig_count - len(saved_windows), len(saved_windows),
            )
        elif match == MatchResult.NO_MATCH:
            orig_count = len(saved_windows)
            saved_windows = filter_to_primary(saved_windows, saved_monitors)
            # Clamp coordinates to current primary
            current_primary = next((m for m in monitors_current if m.get("primary")), None)
            if current_primary:
                for w in saved_windows:
                    placement = w.get("placement", {})
                    nr = placement.get("normal_rect")
                    if nr:
                        placement["normal_rect"] = clamp_rect_to_monitor(nr, current_primary)
            logger.warning(
                "primary monitor mismatch — filtered %d windows, clamped coordinates to current primary",
                orig_count - len(saved_windows),
            )

    # Sort by z_order descending (back to front) so final z-order is correct
    sorted_saved = sorted(saved_windows, key=lambda w: w.get("z_order", 0), reverse=True)

    launched_count = 0
    if running_windows is None:
        from src.launcher import ensure_apps_running
        from src.capture import list_current_windows
        running_windows = list_current_windows()
        launched_count = ensure_apps_running(sorted_saved)
        if stabilize_ms > 0:
            time.sleep(stabilize_ms / 1000.0)
        running_windows = list_current_windows()  # re-scan after launch

    matches = match_windows(sorted_saved, running_windows)

    restored = 0
    failed = 0
    matched_pairs: list[tuple[dict, dict]] = []  # all matched windows (success and fail)
    for saved, running in matches:
        if running is None:
            failed += 1
            continue
        ok = restore_placement(running["hwnd"], saved["placement"])
        matched_pairs.append((saved, running))
        if ok:
            restored += 1
        else:
            failed += 1

    # Post-settle re-apply: some apps (Chrome/Electron) process WM_WINDOWPOSCHANGED
    # asynchronously and restore their own position 1-2 s after SetWindowPos.
    # Others (Chrome on startup) temporarily ignore SetWindowPos while loading
    # their saved state, then become receptive after fully initializing.
    # We wait, then re-apply ALL matched windows regardless of first-pass outcome.
    if post_settle_ms > 0 and matched_pairs:
        logger.info("post-settle: waiting %dms then re-applying %d placement(s)", post_settle_ms, len(matched_pairs))
        time.sleep(post_settle_ms / 1000.0)
        for saved, running in matched_pairs:
            restore_placement(running["hwnd"], saved["placement"])

    if post_launch_settle_ms > 0 and launched_count > 0 and matched_pairs:
        logger.info(
            "post-launch-settle: %d app(s) were launched — waiting %dms then re-applying %d placement(s)",
            launched_count, post_launch_settle_ms, len(matched_pairs),
        )
        time.sleep(post_launch_settle_ms / 1000.0)
        for saved, running in matched_pairs:
            restore_placement(running["hwnd"], saved["placement"])

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "done '%s' — %d/%d restored, %d failed, elapsed %dms",
        layout.get("name", "?"), restored, len(saved_windows), failed, elapsed_ms,
    )
    return {"restored": restored, "failed": failed, "total": len(saved_windows), "elapsed_ms": elapsed_ms}
