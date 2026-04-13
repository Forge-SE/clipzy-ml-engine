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

    # AWS S3 Config
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "clipzy-videos"
    S3_UPLOADS_PREFIX: str = "uploads"

    # Modal Config
    MODAL_TOKEN_ID: str = ""
    MODAL_TOKEN_SECRET: str = ""
    MODAL_GPU_TYPE: str = "A100"
    MODAL_TIMEOUT_SECONDS: int = 3600

    # Assembly AI Config
    ASSEMBLYAI_API_KEY: str = ""

    # RabbitMQ Config
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Celery Config
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672/"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

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
