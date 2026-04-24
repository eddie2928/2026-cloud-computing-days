import logging
import time
from typing import Optional

logger = logging.getLogger("capture")


def _get_placement_state(show_cmd: int) -> str:
    try:
        import win32con
        if show_cmd == win32con.SW_SHOWMINIMIZED:
            return "minimized"
        if show_cmd == win32con.SW_SHOWMAXIMIZED:
            return "maximized"
    except Exception:
        pass
    return "normal"


def _is_cloaked(hwnd: int) -> bool:
    try:
        import ctypes
        DWMWA_CLOAKED = 14
        cloaked = ctypes.c_int(0)
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
        )
        return cloaked.value != 0
    except Exception:
        return False


def _get_exe_path(hwnd: int) -> Optional[str]:
    try:
        import win32process, win32api
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            size = ctypes.c_ulong(1024)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(int(handle), 0, buf, ctypes.byref(size))
            return buf.value
        finally:
            win32api.CloseHandle(handle)
    except Exception as e:
        logger.warning("capture: OpenProcess failed for hwnd=%s: %s", hwnd, e)
        return None


def list_current_windows() -> list[dict]:
    import win32gui, win32con

    t0 = time.perf_counter()
    logger.info("capture: enumerating windows")

    results = []
    all_hwnds = []

    def _enum_cb(hwnd, _):
        all_hwnds.append(hwnd)

    win32gui.EnumWindows(_enum_cb, None)

    skipped = 0
    for i, hwnd in enumerate(all_hwnds):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                logger.debug("capture: skipped invisible hwnd=%s", hwnd)
                skipped += 1
                continue
            title = win32gui.GetWindowText(hwnd)
            if not title:
                logger.debug("capture: skipped no-title hwnd=%s", hwnd)
                skipped += 1
                continue
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW:
                logger.debug("capture: skipped tool window hwnd=%s title='%s'", hwnd, title)
                skipped += 1
                continue
            if _is_cloaked(hwnd):
                logger.debug("capture: skipped cloaked hwnd=%s title='%s'", hwnd, title)
                skipped += 1
                continue

            class_name = win32gui.GetClassName(hwnd)
            exe_path = _get_exe_path(hwnd)
            if exe_path is None:
                logger.warning("capture: skipped hwnd=%s (no exe path)", hwnd)
                skipped += 1
                continue

            placement = win32gui.GetWindowPlacement(hwnd)
            show_cmd = placement[1] if placement else 1
            normal_rect = list(placement[4]) if placement and len(placement) > 4 else [0, 0, 800, 600]
            min_pos = list(placement[2]) if placement and len(placement) > 2 else [-1, -1]
            max_pos = list(placement[3]) if placement and len(placement) > 3 else [-1, -1]
            state = _get_placement_state(show_cmd)

            is_uwp = exe_path.lower().endswith("applicationframehost.exe")

            entry = {
                "hwnd": hwnd,
                "exe_path": exe_path,
                "exe_args": "",
                "cwd": "",
                "title_snapshot": title,
                "title_pattern": "",
                "class_name": class_name,
                "placement": {
                    "state": state,
                    "normal_rect": normal_rect,
                    "min_pos": min_pos,
                    "max_pos": max_pos,
                },
                "monitor_index": 0,
                "z_order": i,
                "is_topmost": False,
                "is_uwp": is_uwp,
            }
            results.append(entry)
            logger.debug(
                "capture: hwnd=0x%x exe=%s title='%s' state=%s rect=%s",
                hwnd, exe_path, title, state, normal_rect
            )
        except Exception as e:
            logger.warning("capture: error processing hwnd=%s: %s", hwnd, e)
            skipped += 1

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info("capture: found %d candidates (%d skipped) in %dms", len(results), skipped, elapsed_ms)
    return results
