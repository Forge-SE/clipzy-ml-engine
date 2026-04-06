"""Application configuration management."""

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App Config
    APP_NAME: str = "Clipzy Video Processing Backend"
    APP_VERSION: str = "0.1.0"
    ENV: Literal["dev", "prod", "test"] = "dev"
    DEBUG: bool = True

    # API Config
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "Clipzy API"
    API_DESCRIPTION: str = "AI-powered video processing with automated editing"

    # Redis Config
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT: int = 10
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 10

    # Storage Config
    STORAGE_TYPE: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "./storage"
    MAX_FILE_SIZE_MB: int = 1000  # 1GB max file size

    # Processing Config
    PROCESSING_TIMEOUT_SECONDS: int = 3600  # 1 hour
    MAX_CONCURRENT_JOBS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def storage_path(self) -> Path:
        """Get the storage path for videos."""
        path = Path(self.LOCAL_STORAGE_PATH)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENV == "prod"


# Global settings instance
settings = Settings()
