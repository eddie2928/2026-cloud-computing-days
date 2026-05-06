from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROXY_PORT: int = 8080
    API_PORT: int = 8000
    DB_PATH: str = "data/agentbox.db"
    CA_DIR: str = "certs"
    HITL_TIMEOUT: float = 300.0
    DEBUG: bool = False


cfg = Settings()
