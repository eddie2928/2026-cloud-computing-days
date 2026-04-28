"""Headless rollback entry point — called by Windows Task Scheduler."""
import ctypes
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )
except Exception:
    pass

import argparse
import logging
import sys
from pathlib import Path

# Ensure src is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logging_setup import LOG_FORMAT, DATE_FORMAT
from src import storage, capture, restore as restore_mod

logger = logging.getLogger("rollback")


def main():
    parser = argparse.ArgumentParser(description="WinLayoutSaver headless rollback")
    parser.add_argument("--layout", default=None, help="Layout name to restore (overrides config)")
    parser.add_argument("--no-launch", action="store_true", help="Skip launching missing apps")
    args = parser.parse_args()

    # Rollback gets its own dated log file
    import os
    from datetime import datetime
    from src.paths import APPDATA
    logs_dir = APPDATA / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rollback_log = logs_dir / f"rollback-{timestamp}.log"

    import logging.handlers
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    fh = logging.handlers.RotatingFileHandler(rollback_log, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    logger.info("rollback: starting (pid=%d)", os.getpid())

    config = storage.load_config()
    rollback_cfg = config.get("auto_rollback", {})
    layout_name = args.layout or rollback_cfg.get("layout_name", "")
    mode = rollback_cfg.get("mode", "fast")
    if mode not in ("fast", "full"):
        logger.warning("rollback: unknown mode '%s', falling back to 'fast'", mode)
        mode = "fast"

    if not layout_name:
        logger.error("rollback: no layout name specified (use --layout or set config)")
        sys.exit(1)

    try:
        layout = storage.load_layout(layout_name)
    except FileNotFoundError:
        logger.error("rollback: layout '%s' not found", layout_name)
        sys.exit(1)

    from src.monitors import list_current_monitors
    monitors_current = list_current_monitors()

    logger.info("--- phase: restore placement (mode=%s) ---", mode)

    if args.no_launch or mode == "fast":
        # fast: 이미 실행 중인 창들만 즉시 재배치 — launch / settle 모두 생략
        running = capture.list_current_windows()
        logger.info("rollback: fast path — %d running windows, no app launching", len(running))
        result = restore_mod.restore_layout(
            layout,
            running_windows=running,
            monitors_current=monitors_current,
            post_settle_ms=2000,
            post_launch_settle_ms=0,
        )
    else:
        # full: 누락 앱 launch + post_launch_settle 5초
        result = restore_mod.restore_layout(
            layout,
            monitors_current=monitors_current,
            post_launch_settle_ms=5000,
        )

    logger.info(
        "rollback: complete — restored %d/%d, failed %d, elapsed %dms",
        result["restored"], result["total"], result["failed"], result["elapsed_ms"],
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
