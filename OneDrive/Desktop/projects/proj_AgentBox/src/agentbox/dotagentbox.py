"""Layout management: ~/.agentbox/ (global config) ↔ <repo>/.agentbox/ (local state)."""
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LayoutPaths:
    global_env: Path
    global_endpoint: Path
    global_sops: Path
    global_certs_dir: Path
    local_pid: Path
    local_logs_dir: Path
    local_last_init: Path


def _global_home() -> Path:
    env_override = os.environ.get("AGENTBOX_HOME")
    if env_override:
        return Path(env_override)
    return Path.home() / ".agentbox"


def _migrate_file(src: Path, dst: Path) -> None:
    """Move src → dst idempotently.

    If dst already exists with different content, back up src as src.backup-<ts>
    and leave dst untouched. Leaves an empty <src>.migrated marker so re-runs skip it.
    """
    marker = src.parent / (src.name + ".migrated")
    if marker.exists() or not src.exists():
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        if src.read_bytes() == dst.read_bytes():
            src.unlink()
        else:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = src.parent / f"{src.name}.backup-{ts}"
            src.rename(backup)
    else:
        shutil.move(str(src), str(dst))

    marker.write_bytes(b"")


def _migrate_dir(src_dir: Path, dst_dir: Path) -> None:
    """Move all files from src_dir to dst_dir idempotently.

    Skips files that already exist in dst_dir. Leaves a .migrated marker in src_dir.
    """
    if not src_dir.is_dir():
        return

    marker = src_dir / ".migrated"
    if marker.exists():
        return

    dst_dir.mkdir(parents=True, exist_ok=True)

    for item in list(src_dir.iterdir()):
        if item.name == ".migrated":
            continue
        if item.is_file():
            dst_item = dst_dir / item.name
            if not dst_item.exists():
                shutil.move(str(item), str(dst_item))
            else:
                item.unlink()

    marker.write_bytes(b"")


def ensure_layout(project_root: Path) -> LayoutPaths:
    """Ensure global config and local state directories exist; run one-time migration.

    Args:
        project_root: The repo root (parent of .agentbox/ local state dir).

    Returns:
        LayoutPaths with canonical paths for all config/state artifacts.
    """
    global_home = _global_home()
    local_state = project_root / ".agentbox"

    # Create directory structure
    global_home.mkdir(parents=True, exist_ok=True)
    (global_home / "certs" / "grpc").mkdir(parents=True, exist_ok=True)
    (local_state / "logs").mkdir(parents=True, exist_ok=True)

    # One-time migration: config files → global home
    _migrate_file(project_root / ".env", global_home / "env")
    _migrate_file(project_root / ".env.endpoint", global_home / "endpoint")
    _migrate_file(project_root / ".sops.yaml", global_home / "sops.yaml")

    # One-time migration: certs → global home
    _migrate_dir(project_root / "certs" / "grpc", global_home / "certs" / "grpc")

    # One-time migration: pid + logs → local state
    _migrate_file(project_root / ".agentbox.pid", local_state / "pid")
    _migrate_dir(project_root / "logs", local_state / "logs")

    # One-time migration: old user-wide last_init.json → project-local
    old_last_init = global_home / "last_init.json"
    new_last_init = local_state / "last_init.json"
    if old_last_init.exists() and not new_last_init.exists():
        shutil.move(str(old_last_init), str(new_last_init))

    return LayoutPaths(
        global_env=global_home / "env",
        global_endpoint=global_home / "endpoint",
        global_sops=global_home / "sops.yaml",
        global_certs_dir=global_home / "certs" / "grpc",
        local_pid=local_state / "pid",
        local_logs_dir=local_state / "logs",
        local_last_init=local_state / "last_init.json",
    )
