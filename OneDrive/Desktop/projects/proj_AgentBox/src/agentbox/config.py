import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, str]:
    home = os.environ.get("AGENTBOX_HOME")
    base = Path(home) if home else Path.home() / ".agentbox"
    return (str(base / "env"), str(base / "endpoint"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROXY_PORT: int = 8080
    API_PORT: int = 8000
    DB_PATH: str = "data/agentbox.db"
    CA_DIR: str = "certs"
    HITL_TIMEOUT: float = 300.0
    DEBUG: bool = False

    # Phase 1B: EC2 gRPC endpoint
    GRPC_HOST: str = ""
    GRPC_PORT: int = 50051
    GRPC_TIMEOUT: float = 60.0
    GRPC_CA_CERT: str = ""
    GRPC_CLIENT_CERT: str = ""
    GRPC_CLIENT_KEY: str = ""


cfg = Settings()
