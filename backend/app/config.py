import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    STORAGE_ROOT: str = "./storage"
    REDIS_URL: str = "redis://localhost:6379"
    API_KEY: str = "changeme"
    DEFAULT_QUALITY: int = 1080
    DEFAULT_FORMAT: str = "mp4"
    MAX_CONCURRENT_DOWNLOADS: int = 3
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_PATH(self) -> str:
        """Derive database path from storage root."""
        storage = Path(self.STORAGE_ROOT)
        db_dir = storage / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "videos.db")

    @property
    def CATEGORIES_DIR(self) -> str:
        """Derive categories directory path."""
        storage = Path(self.STORAGE_ROOT)
        categories_dir = storage / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)
        return str(categories_dir)

    @property
    def THUMBNAILS_DIR(self) -> str:
        """Derive thumbnails directory path."""
        storage = Path(self.STORAGE_ROOT)
        thumbnails_dir = storage / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        return str(thumbnails_dir)


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
