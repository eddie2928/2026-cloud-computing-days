"""Read/write ~/.agentbox/last_init.json for agentbox init metadata persistence."""
import json
import logging
from pathlib import Path

logger = logging.getLogger("agentbox.last_init")

_DEFAULT_PATH = Path.home() / ".agentbox" / "last_init.json"


def write(meta: dict, path: Path | None = None) -> None:
    target = path or _DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)


def read(path: Path | None = None) -> dict | None:
    target = path or _DEFAULT_PATH
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to parse last_init.json: %s", exc)
        return None
