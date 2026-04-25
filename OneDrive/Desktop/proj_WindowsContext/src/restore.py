import logging
import re
import time
from typing import Optional

logger = logging.getLogger("restore")


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


def restore_placement(hwnd: int, placement: dict) -> bool:
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

        # SetWindowPlacement sets state + normal_rect atomically
        win32gui.SetWindowPlacement(hwnd, (
            0,          # flags
            show_cmd,
            min_pos,
            max_pos,
            ltrb,       # rcNormalPosition in LTRB
        ))
        logger.info("placed hwnd=0x%x state=%s rect=%s", hwnd, state, nr)
        return True
    except OSError as e:
        logger.warning("failed to place hwnd=0x%x: %s", hwnd, e)
        return False


def restore_layout(layout: dict, running_windows: list[dict] = None, monitors_current: list[dict] = None) -> dict:
    """
    Restore a saved layout by matching saved windows to running windows
    and repositioning them.

    Args:
        layout: loaded layout dict (from storage.load_layout)
        running_windows: list of current windows (from capture.list_current_windows).
                         If None, captures current windows.
        monitors_current: current monitor list. If provided, applies monitor gate policy.

    Returns:
        {"restored": int, "failed": int, "total": int, "elapsed_ms": int}
    """
    from src.monitors import compare_monitors, filter_to_primary, clamp_rect_to_monitor, MatchResult

    t0 = time.perf_counter()
    saved_windows = layout.get("windows", [])
    saved_monitors = layout.get("monitors", [])

    logger.info("starting '%s' (%d windows)", layout.get("name", "?"), len(saved_windows))

    if running_windows is None:
        from src.capture import list_current_windows
        running_windows = list_current_windows()

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

    matches = match_windows(sorted_saved, running_windows)

    restored = 0
    failed = 0
    for saved, running in matches:
        if running is None:
            failed += 1
            continue
        ok = restore_placement(running["hwnd"], saved["placement"])
        if ok:
            restored += 1
        else:
            failed += 1

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "done '%s' — %d/%d restored, %d failed, elapsed %dms",
        layout.get("name", "?"), restored, len(saved_windows), failed, elapsed_ms,
    )
    return {"restored": restored, "failed": failed, "total": len(saved_windows), "elapsed_ms": elapsed_ms}
