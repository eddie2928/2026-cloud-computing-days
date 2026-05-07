from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROXY_PORT: int = 8080
    API_PORT: int = 8000
    DB_PATH: str = "data/agentbox.db"
    CA_DIR: str = "certs"
    HITL_TIMEOUT: float = 300.0
    DEBUG: bool = False

    # Phase 1A: transparent interception (iptables REDIRECT, no HTTPS_PROXY needed)
    TRANSPARENT_MODE: bool = False
    EBPF_STATS_LOG: str = "logs/ebpf-stats.log"

    # Phase 1B: EC2 gRPC endpoint
    GRPC_HOST: str = ""
    GRPC_PORT: int = 50051
    GRPC_TIMEOUT: float = 5.0
    GRPC_CA_CERT: str = ""   # path to agentbox-ca.crt for mTLS
    GRPC_CLIENT_CERT: str = ""  # path to endpoint.crt
    GRPC_CLIENT_KEY: str = ""   # path to endpoint.key


cfg = Settings()
