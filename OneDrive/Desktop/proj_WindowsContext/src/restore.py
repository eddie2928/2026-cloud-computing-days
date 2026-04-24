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
        best_hwnd = None
        best_score = 0
        for running in running_windows:
            s = score_window(saved, running, assigned_hwnds)
            if s > best_score:
                best_score = s
                best_hwnd = running["hwnd"]
        if best_hwnd is not None:
            assigned_hwnds.add(best_hwnd)
            matched = next(r for r in running_windows if r["hwnd"] == best_hwnd)
            results.append((saved, matched))
            logger.info(
                "matched saved '%s' → hwnd=0x%x score=%d",
                saved.get("title_snapshot", saved.get("exe_path", "")),
                best_hwnd,
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
        import win32gui, win32con
        state = placement.get("state", "normal")
        normal_rect = placement.get("normal_rect", [0, 0, 800, 600])
        min_pos = tuple(placement.get("min_pos", [-1, -1]))
        max_pos = tuple(placement.get("max_pos", [-1, -1]))

        if state == "minimized":
            show_cmd = win32con.SW_SHOWMINIMIZED
        elif state == "maximized":
            show_cmd = win32con.SW_SHOWMAXIMIZED
        else:
            show_cmd = win32con.SW_SHOWNORMAL

        # SetWindowPlacement sets state + normal_rect atomically
        win32gui.SetWindowPlacement(hwnd, (
            0,          # flags
            show_cmd,
            min_pos,
            max_pos,
            tuple(normal_rect),
        ))
        logger.info(
            "placed hwnd=0x%x state=%s rect=%s",
            hwnd, state, normal_rect,
        )
        return True
    except Exception as e:
        logger.warning("failed to place hwnd=0x%x: %s", hwnd, e)
        return False


def restore_layout(layout: dict, running_windows: list[dict] = None) -> dict:
    """
    Restore a saved layout by matching saved windows to running windows
    and repositioning them.

    Args:
        layout: loaded layout dict (from storage.load_layout)
        running_windows: list of current windows (from capture.list_current_windows).
                         If None, captures current windows.

    Returns:
        {"restored": int, "failed": int, "total": int, "elapsed_ms": int}
    """
    t0 = time.perf_counter()
    saved_windows = layout.get("windows", [])
    logger.info("restore: starting '%s' (%d windows)", layout.get("name", "?"), len(saved_windows))

    if running_windows is None:
        from src.capture import list_current_windows
        running_windows = list_current_windows()

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
        "restore: done '%s' — %d/%d restored, %d failed, elapsed %dms",
        layout.get("name", "?"), restored, len(saved_windows), failed, elapsed_ms,
    )
    return {"restored": restored, "failed": failed, "total": len(saved_windows), "elapsed_ms": elapsed_ms}
