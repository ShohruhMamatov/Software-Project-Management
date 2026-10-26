"""App settings, read from environment variables (and the repo-root .env file if it exists)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repo root is two folders up from app/
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Real environment variables (e.g. from docker-compose) win over the .env file.
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    app_name: str = "LUMI API"
    database_url: str = "postgresql+psycopg://lumi:change-me@localhost:5432/lumi"
    media_dir: str = "./media"


settings = Settings()
