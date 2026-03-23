"""Shared test fixtures for the backend test suite."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import aiosqlite
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.database import init_db


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory structure."""
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "db").mkdir()
    (storage / "categories").mkdir()
    (storage / "thumbnails").mkdir()
    return storage


@pytest.fixture
def settings(tmp_storage: Path) -> Settings:
    """Create test settings pointing to temporary storage."""
    return Settings(
        STORAGE_ROOT=str(tmp_storage),
        API_KEY="test-api-key",
        DEFAULT_QUALITY=720,
        DEFAULT_FORMAT="mp4",
        MAX_CONCURRENT_DOWNLOADS=2,
    )


@pytest_asyncio.fixture
async def db(settings: Settings) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Create and initialize a test database, yield a connection."""
    await init_db(settings.DATABASE_PATH)
    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn


@pytest_asyncio.fixture
async def db_with_videos(db: aiosqlite.Connection) -> aiosqlite.Connection:
    """Seed the test database with sample videos."""
    videos = [
        ("vid-1", "https://youtube.com/watch?v=abc", "youtube", "abc",
         "Python Tutorial for Beginners", "Learn Python step by step",
         "CodeChannel", "2024-01-15", 1800, "1080p",
         "categories/tutorials/python_tutorial.mp4", 150_000_000,
         None, "tutorials", "completed", None, 100.0),
        ("vid-2", "https://youtube.com/watch?v=def", "youtube", "def",
         "Epic Gaming Montage", "Best plays of the year",
         "GamePro", "2024-02-20", 600, "720p",
         "categories/gaming/epic_montage.mp4", 80_000_000,
         None, "gaming", "completed", None, 100.0),
        ("vid-3", "https://instagram.com/reel/xyz", "instagram", "xyz",
         "Quick cooking tip", None,
         "chef_daily", "2024-03-10", 30, None,
         "categories/short-form/cooking_tip.mp4", 5_000_000,
         None, "short-form", "completed", None, 100.0),
        ("vid-4", "https://youtube.com/watch?v=ghi", "youtube", "ghi",
         "Breaking News Update", "Latest world news",
         "NewsNet", "2024-04-01", 300, "1080p",
         None, None,
         None, "news", "failed", "Download timeout", 0.0),
    ]

    for v in videos:
        await db.execute(
            """INSERT INTO videos
               (id, source_url, platform, platform_id, title, description,
                uploader, upload_date, duration_secs, resolution,
                file_path, file_size_bytes, thumbnail_path, category,
                status, error_message, progress)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            v,
        )

    # Add tags
    await db.execute("INSERT INTO tags (name) VALUES (?)", ("python",))
    await db.execute("INSERT INTO tags (name) VALUES (?)", ("beginner",))
    await db.execute("INSERT INTO tags (name) VALUES (?)", ("gaming",))

    # Link tags to videos
    await db.execute(
        "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", ("vid-1", 1)
    )
    await db.execute(
        "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", ("vid-1", 2)
    )
    await db.execute(
        "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", ("vid-2", 3)
    )

    # Populate FTS index
    for vid_id, title, desc, uploader in [
        ("vid-1", "Python Tutorial for Beginners", "Learn Python step by step", "CodeChannel"),
        ("vid-2", "Epic Gaming Montage", "Best plays of the year", "GamePro"),
        ("vid-3", "Quick cooking tip", "", "chef_daily"),
        ("vid-4", "Breaking News Update", "Latest world news", "NewsNet"),
    ]:
        cursor = await db.execute("SELECT rowid FROM videos WHERE id = ?", (vid_id,))
        row = await cursor.fetchone()
        rowid = row[0]
        tags_cursor = await db.execute(
            "SELECT GROUP_CONCAT(t.name, ' ') FROM video_tags vt JOIN tags t ON vt.tag_id = t.id WHERE vt.video_id = ?",
            (vid_id,),
        )
        tags_row = await tags_cursor.fetchone()
        tags_str = tags_row[0] or ""
        await db.execute(
            "INSERT INTO videos_fts(rowid, title, description, uploader, tags) VALUES(?,?,?,?,?)",
            (rowid, title, desc or "", uploader or "", tags_str),
        )

    await db.commit()
    return db
