from functools import lru_cache

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server-side LLM connection settings."""

    base_url: AnyHttpUrl = "http://localhost:11434/v1/"  # type: ignore[assignment]
    api_key: SecretStr = SecretStr("ollama")
    model: str = "llama3.2"
    request_timeout: float = 120.0
    public_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")

    @property
    def api_key_value(self) -> str:
        return self.api_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
