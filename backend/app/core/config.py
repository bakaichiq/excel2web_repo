from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = Field(default="dev")  # dev|prod
    TZ: str = Field(default="Asia/Bishkek")

    # Security
    JWT_SECRET: str = Field(default="change-me")
    JWT_ALG: str = Field(default="HS256")
    JWT_EXPIRES_MIN: int = Field(default=60 * 12)

    # DB
    DATABASE_URL: str = Field(default="postgresql+psycopg://app:app@db:5432/app")

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://localhost")

    # Celery / Redis
    REDIS_URL: str = Field(default="redis://redis:6379/0")

    # Files
    UPLOAD_DIR: str = Field(default="/app/data/uploads")
    EXPORT_DIR: str = Field(default="/app/data/exports")

    # Business defaults
    SHIFT_HOURS: float = Field(default=8.0)
    OPENING_CASH_BALANCE: float = Field(default=0.0)

    # Seed (dev)
    SEED_DEMO: bool = Field(default=True)
    DEMO_ADMIN_LOGIN: str = Field(default="admin")
    DEMO_ADMIN_PASSWORD: str = Field(default="admin123")


settings = Settings()
