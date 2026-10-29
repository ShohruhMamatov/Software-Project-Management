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

    # JWT for dashboard users. The default is for local dev only; set a real secret in .env.
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 12

    # Any secret string; a Fernet key is derived from it to encrypt camera passwords.
    # Changing it makes already-saved camera passwords unreadable.
    camera_enc_key: str = "dev-only-change-me"

    # Frontend origins allowed to call the API (comma-separated).
    cors_origins: str = "http://localhost:5173"

    # A camera counts as "online" if the edge agent reported it within this many seconds.
    camera_online_seconds: int = 120


settings = Settings()
