"""Unit tests for config.py multi-path env_file loading (Task-7 A2)."""
from pathlib import Path

import pytest

from pydantic_settings import BaseSettings, SettingsConfigDict


def _make_settings(env_file: tuple[str, str], **field_defaults):
    """Instantiate a fresh Settings with explicit env file paths (no module reload needed)."""
    from agentbox.config import Settings
    return Settings(_env_file=env_file)


# ── T1: ~/.agentbox/env → GRPC_HOST ─────────────────────────────────────────
def test_loads_grpc_host_from_global_env(tmp_path):
    env_file = tmp_path / "env"
    env_file.write_text("GRPC_HOST=testhost\n", encoding="utf-8")
    endpoint_file = tmp_path / "endpoint"
    endpoint_file.write_text("EC2_GRPC_HOST=ec2host\n", encoding="utf-8")

    from agentbox.config import Settings
    s = Settings(_env_file=(str(env_file), str(endpoint_file)))

    assert s.GRPC_HOST == "testhost"


# ── T2: 두 파일 다 없으면 기본값 fallback ────────────────────────────────────
def test_defaults_when_no_env_files(tmp_path):
    missing1 = str(tmp_path / "noenv")
    missing2 = str(tmp_path / "noendpoint")

    from agentbox.config import Settings
    s = Settings(_env_file=(missing1, missing2))

    assert s.GRPC_HOST == ""
    assert s.GRPC_PORT == 50051
    assert s.PROXY_PORT == 8080


# ── T3: endpoint 파일이 env 파일의 같은 키를 override ────────────────────────
def test_endpoint_overrides_env(tmp_path):
    env_file = tmp_path / "env"
    env_file.write_text("GRPC_HOST=from-env\n", encoding="utf-8")
    endpoint_file = tmp_path / "endpoint"
    endpoint_file.write_text("GRPC_HOST=from-endpoint\n", encoding="utf-8")

    from agentbox.config import Settings
    s = Settings(_env_file=(str(env_file), str(endpoint_file)))

    # Later file (endpoint) overrides earlier (env)
    assert s.GRPC_HOST == "from-endpoint"
