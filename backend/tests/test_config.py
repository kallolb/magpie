"""Tests for app.config."""

import os
import pytest
from pathlib import Path

from app.config import Settings, get_settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_values(self):
        s = Settings(STORAGE_ROOT="/tmp/test-storage")
        assert s.DEFAULT_QUALITY == 1080
        assert s.DEFAULT_FORMAT == "mp4"
        assert s.MAX_CONCURRENT_DOWNLOADS == 3
        assert s.API_HOST == "0.0.0.0"
        assert s.API_PORT == 8000

    def test_database_path_derived(self, tmp_path):
        s = Settings(STORAGE_ROOT=str(tmp_path))
        assert s.DATABASE_PATH.endswith("db/videos.db")
        assert str(tmp_path) in s.DATABASE_PATH

    def test_database_path_creates_directory(self, tmp_path):
        storage = tmp_path / "new_storage"
        s = Settings(STORAGE_ROOT=str(storage))
        _ = s.DATABASE_PATH
        assert (storage / "db").exists()

    def test_categories_dir_derived(self, tmp_path):
        s = Settings(STORAGE_ROOT=str(tmp_path))
        assert s.CATEGORIES_DIR.endswith("categories")

    def test_thumbnails_dir_derived(self, tmp_path):
        s = Settings(STORAGE_ROOT=str(tmp_path))
        assert s.THUMBNAILS_DIR.endswith("thumbnails")

    def test_custom_api_key(self):
        s = Settings(STORAGE_ROOT="/tmp/test", API_KEY="my-secret-key")
        assert s.API_KEY == "my-secret-key"

    def test_custom_quality(self):
        s = Settings(STORAGE_ROOT="/tmp/test", DEFAULT_QUALITY=720)
        assert s.DEFAULT_QUALITY == 720


class TestGetSettings:
    """Tests for get_settings() factory."""

    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)
