import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("scheduler")

TASK_NAME = "WinLayoutSaver_Rollback"


def _delay_str(seconds: int) -> str:
    """Convert seconds to schtasks DELAY format: HHMM:SS"""
    hours = seconds // 3600
    remaining = seconds % 3600
    minutes = remaining // 60
    secs = remaining % 60
    return f"{hours:02d}{minutes:02d}:{secs:02d}"


def register(script_path: str, delay_seconds: int = 20, python_exe: str = None) -> bool:
    """
    Register WinLayoutSaver_Rollback in Windows Task Scheduler.
    Runs at logon with a startup delay. No admin rights needed (/RL LIMITED).
    Returns True on success.
    """
    if python_exe is None:
        python_dir = Path(sys.executable).parent
        pythonw = python_dir / "pythonw.exe"
        if not pythonw.exists():
            pythonw = Path(sys.executable)  # fallback
        python_exe = str(pythonw)

    delay = _delay_str(delay_seconds)
    tr = f'"{python_exe}" "{script_path}"'

    cmd = [
        "schtasks.exe",
        "/Create",
        "/TN", TASK_NAME,
        "/TR", tr,
        "/SC", "ONLOGON",
        "/DELAY", delay,
        "/RL", "LIMITED",
        "/F",
    ]

    logger.info("scheduler: registering task — %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("scheduler: schtasks exit=%d stdout=%s", result.returncode, result.stdout.strip())
    if result.returncode != 0:
        logger.error("scheduler: registration failed — stderr=%s", result.stderr)
        return False
    return True


def unregister() -> bool:
    """
    Remove WinLayoutSaver_Rollback from Windows Task Scheduler.
    Returns True on success.
    """
    cmd = [
        "schtasks.exe",
        "/Delete",
        "/TN", TASK_NAME,
        "/F",
    ]
    logger.info("scheduler: unregistering task — %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("scheduler: schtasks exit=%d", result.returncode)
    if result.returncode != 0:
        logger.error("scheduler: unregister failed — stderr=%s", result.stderr)
        return False
    return True
