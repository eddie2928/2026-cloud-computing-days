import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("storage")

APPDATA = Path(os.environ.get("APPDATA", Path.home())) / "WinLayoutSaver"
LAYOUTS_DIR = APPDATA / "layouts"
CONFIG_PATH = APPDATA / "config.json"


def _ensure_dirs():
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)


def save_layout(name: str, layout_data: dict) -> Path:
    _ensure_dirs()
    path = LAYOUTS_DIR / f"{name}.json"
    logger.info("storage: saving layout '%s' to %s", name, path)
    try:
        path.write_text(json.dumps(layout_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        logger.error("storage: failed to write %s: %s", path, e)
        raise
    windows_count = len(layout_data.get("windows", []))
    logger.info("storage: saved '%s' (%d windows)", name, windows_count)
    return path


def load_layout(name: str) -> dict:
    path = LAYOUTS_DIR / f"{name}.json"
    logger.info("storage: loading layout '%s' from %s", name, path)
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("storage: JSON parse error in %s: %s", path, e)
        raise ValueError(f"Corrupted layout file: {path}") from e
    logger.info("storage: loaded '%s' (%d windows)", name, len(data.get("windows", [])))
    return data


def list_layouts() -> list[str]:
    if not LAYOUTS_DIR.exists():
        return []
    return sorted(p.stem for p in LAYOUTS_DIR.glob("*.json"))


def delete_layout(name: str) -> None:
    path = LAYOUTS_DIR / f"{name}.json"
    path.unlink(missing_ok=True)
    logger.info("storage: deleted layout '%s'", name)


def next_layout_name() -> str:
    existing = set(list_layouts())
    i = 1
    while f"Screen{i}" in existing:
        i += 1
    return f"Screen{i}"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return _default_config()
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_config()


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _default_config() -> dict:
    return {
        "auto_rollback": {
            "enabled": False,
            "layout_name": "",
            "startup_delay_seconds": 20,
            "app_launch_timeout_seconds": 60,
            "per_window_retry_ms": 500,
        },
        "ui": {"language": "ko"},
    }
