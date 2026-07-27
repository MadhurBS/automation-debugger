from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Automation Project Debugger"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = True

    # Database (SQLite by default for local dev; switch to postgresql+asyncpg://... for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./automation_debugger.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.2

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = [
        # Archives / project packages
        ".zip", ".nupkg",
        # UiPath
        ".xaml",
        # Blue Prism
        ".bprelease", ".bpprocess", ".bpobject",
        # Automation Anywhere
        ".atmx", ".mbot",
        # Power Automate / generic
        ".json", ".xml",
        # Log files
        ".log", ".txt",
    ]
    REPORTS_DIR: str = "./reports"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("UPLOAD_DIR", "REPORTS_DIR", mode="after")
    @classmethod
    def create_dirs(cls, v: str) -> str:
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


settings = Settings()
