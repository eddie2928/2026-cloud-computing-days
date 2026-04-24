import logging
import re
import subprocess
import time
from typing import Optional

import psutil

from src.capture import list_current_windows

logger = logging.getLogger("launcher")


def is_running(exe_path: str) -> bool:
    """Check if any process with this exe path is currently running."""
    exe_lower = exe_path.lower()
    for proc in psutil.process_iter(["exe"]):
        try:
            proc_exe = proc.info.get("exe") or ""
            if proc_exe.lower() == exe_lower:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def launch_app(exe_path: str, exe_args: str = "", cwd: str = "", is_uwp: bool = False) -> Optional[subprocess.Popen]:
    """
    Launch an application.
    For UWP apps, uses `explorer.exe shell:AppsFolder\\<AUMID>`.
    Returns the Popen object or None on failure.
    """
    if is_uwp:
        aumid = exe_args.strip()
        cmd = ["explorer.exe", f"shell:AppsFolder\\{aumid}"]
        logger.info("launching UWP app shell:AppsFolder\\%s", aumid)
    else:
        args = exe_args.split() if exe_args else []
        cmd = [exe_path] + args
        logger.info("launching %s args=%s", exe_path, args)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or None,
            shell=False,
            creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0,
        )
        return proc
    except OSError as e:
        logger.error("failed to launch %s: %s", exe_path, e)
        return None


def wait_for_window(
    exe_path: str,
    title_pattern: str,
    timeout_seconds: float = 60.0,
    poll_ms: int = 500,
) -> bool:
    """
    Poll until a window from exe_path matching title_pattern appears,
    or timeout_seconds elapses.
    Returns True if window found, False on timeout.
    """
    exe_lower = exe_path.lower()
    pattern_re = re.compile(title_pattern) if title_pattern else None
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        windows = list_current_windows()
        for w in windows:
            if w.get("exe_path", "").lower() != exe_lower:
                continue
            if pattern_re is None or pattern_re.search(w.get("title_snapshot", "")):
                elapsed = timeout_seconds - (deadline - time.monotonic())
                logger.info("matched after %.1fs — exe=%s title='%s'", elapsed, exe_path, w.get("title_snapshot", ""))
                return True
        logger.debug("polling for window exe=%s pattern='%s'", exe_path, title_pattern)
        time.sleep(poll_ms / 1000.0)

    logger.warning("timeout after %.0fs waiting for exe=%s pattern='%s'", timeout_seconds, exe_path, title_pattern)
    return False


def ensure_apps_running(
    saved_windows: list[dict],
    timeout_seconds: float = 60.0,
    poll_ms: int = 500,
) -> None:
    """
    For each saved window whose app is not running, launch it and wait for its window.
    Missing apps are launched in sequence (not parallel) to avoid race conditions.
    """
    not_running = [w for w in saved_windows if not is_running(w.get("exe_path", ""))]
    logger.info(
        "%d of %d apps not running — will launch: %s",
        len(not_running),
        len(saved_windows),
        [w.get("exe_path", "") for w in not_running],
    )

    for saved in not_running:
        exe_path = saved.get("exe_path", "")
        exe_args = saved.get("exe_args", "")
        cwd = saved.get("cwd", "")
        is_uwp = saved.get("is_uwp", False)
        title_pattern = saved.get("title_pattern", "")

        proc = launch_app(exe_path, exe_args, cwd, is_uwp)
        if proc is None:
            continue

        found = wait_for_window(exe_path, title_pattern, timeout_seconds, poll_ms)
        if not found:
            logger.warning("giving up on '%s' — window did not appear in %.0fs", exe_path, timeout_seconds)
