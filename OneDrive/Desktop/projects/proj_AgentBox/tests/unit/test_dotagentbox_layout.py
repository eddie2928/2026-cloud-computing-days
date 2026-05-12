"""Unit tests for src/agentbox/dotagentbox.py — LayoutPaths + ensure_layout + migration."""
from pathlib import Path

import pytest

from agentbox.dotagentbox import LayoutPaths, ensure_layout, _global_home


# ── T1: 빈 HOME + 빈 repo에서 디렉토리 구조 생성 ─────────────────────────────
def test_ensure_layout_creates_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    project_root = tmp_path / "repo"
    project_root.mkdir()

    layout = ensure_layout(project_root)

    # Global dirs
    assert (tmp_path / "global").is_dir()
    assert (tmp_path / "global" / "certs" / "grpc").is_dir()
    # Local dirs
    assert (project_root / ".agentbox").is_dir()
    assert (project_root / ".agentbox" / "logs").is_dir()

    # LayoutPaths fields point to correct paths
    assert layout.global_env == tmp_path / "global" / "env"
    assert layout.global_endpoint == tmp_path / "global" / "endpoint"
    assert layout.global_sops == tmp_path / "global" / "sops.yaml"
    assert layout.global_certs_dir == tmp_path / "global" / "certs" / "grpc"
    assert layout.local_pid == project_root / ".agentbox" / "pid"
    assert layout.local_logs_dir == project_root / ".agentbox" / "logs"
    assert layout.local_last_init == project_root / ".agentbox" / "last_init.json"


# ── T2: .env 이동 + 원본 삭제 ────────────────────────────────────────────────
def test_migrate_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / ".env").write_text("GRPC_HOST=1.2.3.4\n")

    ensure_layout(project_root)

    assert (tmp_path / "global" / "env").read_text() == "GRPC_HOST=1.2.3.4\n"
    assert not (project_root / ".env").exists()
    assert (project_root / ".env.migrated").exists()


# ── T3: ~/.agentbox/env 이미 존재 + 내용 다름 → backup 생성 ──────────────────
def test_migrate_env_backup_on_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    global_home = tmp_path / "global"
    global_home.mkdir(parents=True)
    (global_home / "env").write_text("GRPC_HOST=existing\n")

    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / ".env").write_text("GRPC_HOST=different\n")

    ensure_layout(project_root)

    # Destination preserved
    assert (global_home / "env").read_text() == "GRPC_HOST=existing\n"
    # Original .env is gone (renamed to backup)
    assert not (project_root / ".env").exists()
    # A backup file was created
    backups = list(project_root.glob(".env.backup-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "GRPC_HOST=different\n"
    # Marker created
    assert (project_root / ".env.migrated").exists()


# ── T4: 두 번 호출해도 결과 동일 (idempotent) ─────────────────────────────────
def test_ensure_layout_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / ".env").write_text("GRPC_HOST=1.2.3.4\n")

    layout1 = ensure_layout(project_root)
    layout2 = ensure_layout(project_root)

    assert layout1.global_env == layout2.global_env
    # Migration happened once; second call is no-op
    assert (tmp_path / "global" / "env").exists()
    # No duplicate backups
    assert len(list(project_root.glob(".env.backup-*"))) == 0


# ── T5: certs/grpc/* 4개 파일 → ~/.agentbox/certs/grpc/ ──────────────────────
def test_migrate_certs(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    project_root = tmp_path / "repo"
    certs_dir = project_root / "certs" / "grpc"
    certs_dir.mkdir(parents=True)
    for name in ("agentbox-ca.crt", "agentbox-ca.key", "endpoint.crt", "endpoint.key"):
        (certs_dir / name).write_text(f"CERT:{name}")

    ensure_layout(project_root)

    dst_dir = tmp_path / "global" / "certs" / "grpc"
    for name in ("agentbox-ca.crt", "agentbox-ca.key", "endpoint.crt", "endpoint.key"):
        assert (dst_dir / name).read_text() == f"CERT:{name}"
    # Source dir gets .migrated marker
    assert (certs_dir / ".migrated").exists()


# ── T6: ~/.agentbox/last_init.json → <repo>/.agentbox/last_init.json ─────────
def test_migrate_last_init(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTBOX_HOME", str(tmp_path / "global"))
    global_home = tmp_path / "global"
    global_home.mkdir(parents=True)
    (global_home / "last_init.json").write_text('{"project_id":"x"}')

    project_root = tmp_path / "repo"
    project_root.mkdir()

    ensure_layout(project_root)

    local_last_init = project_root / ".agentbox" / "last_init.json"
    assert local_last_init.read_text() == '{"project_id":"x"}'
    assert not (global_home / "last_init.json").exists()


# ── T7: AGENTBOX_HOME 환경변수 시 global 경로가 그 아래로 ─────────────────────
def test_agentbox_home_override(tmp_path, monkeypatch):
    custom_home = tmp_path / "custom_agentbox"
    monkeypatch.setenv("AGENTBOX_HOME", str(custom_home))
    project_root = tmp_path / "repo"
    project_root.mkdir()

    layout = ensure_layout(project_root)

    # Global paths are under AGENTBOX_HOME
    assert layout.global_env.is_relative_to(custom_home)
    assert layout.global_certs_dir.is_relative_to(custom_home)
    assert layout.global_sops.is_relative_to(custom_home)
    # Local paths are under project_root
    assert layout.local_logs_dir.is_relative_to(project_root)
    assert layout.local_last_init.is_relative_to(project_root)
    # Directories created
    assert custom_home.is_dir()
    assert (project_root / ".agentbox" / "logs").is_dir()
