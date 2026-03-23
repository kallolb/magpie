import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import aiosqlite
import structlog

logger = structlog.get_logger()

# Default categories to be inserted on initialization
DEFAULT_CATEGORIES = [
    ("uncategorized", "Videos not yet categorized"),
    ("music", "Music videos and songs"),
    ("tutorials", "Tutorial and how-to videos"),
    ("entertainment", "Entertainment and comedy"),
    ("cooking", "Cooking and recipes"),
    ("short-form", "Short-form content"),
    ("sports", "Sports and athletics"),
    ("tech", "Technology and programming"),
    ("news", "News and current events"),
    ("gaming", "Gaming and gameplay"),
]


async def init_db(db_path: str) -> None:
    """Initialize database with schema and default categories."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Enable WAL mode for better concurrency
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA synchronous = NORMAL")

        # Create tables
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                platform TEXT NOT NULL,
                platform_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                uploader TEXT,
                upload_date TEXT,
                duration_secs INTEGER,
                resolution TEXT,
                file_path TEXT,
                file_size_bytes INTEGER,
                thumbnail_path TEXT,
                category TEXT NOT NULL DEFAULT 'uncategorized',
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                progress REAL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            );

            CREATE TABLE IF NOT EXISTS video_tags (
                video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (video_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
                title, description, uploader, tags
            );

            CREATE TABLE IF NOT EXISTS download_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL REFERENCES videos(id),
                triggered_by TEXT,
                triggered_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                status TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_videos_platform_id ON videos(platform_id);
            CREATE INDEX IF NOT EXISTS idx_videos_category ON videos(category);
            CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
            CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);
            CREATE INDEX IF NOT EXISTS idx_video_tags_tag_id ON video_tags(tag_id);
            CREATE INDEX IF NOT EXISTS idx_download_log_video_id ON download_log(video_id);
        """
        )

        # Insert default categories
        for name, description in DEFAULT_CATEGORIES:
            try:
                await db.execute(
                    "INSERT INTO categories (name, description) VALUES (?, ?)",
                    (name, description),
                )
            except sqlite3.IntegrityError:
                # Category already exists
                pass

        await db.commit()

    logger.info("database_initialized", db_path=db_path)


async def get_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI dependency for database connections."""
    async with aiosqlite.connect(db_path) as db:
        # Enable row factory for dict-like access
        db.row_factory = aiosqlite.Row
        yield db


async def get_db_dep() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI Depends()-compatible dependency that resolves db_path from settings."""
    from app.config import get_settings
    settings = get_settings()
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def execute_query(
    db: aiosqlite.Connection, query: str, params: tuple[Any, ...] = ()
) -> None:
    """Execute a query without returning results."""
    await db.execute(query, params)
    await db.commit()


async def fetch_all(
    db: aiosqlite.Connection, query: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    """Fetch all rows from a query."""
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def fetch_one(
    db: aiosqlite.Connection, query: str, params: tuple[Any, ...] = ()
) -> Optional[dict[str, Any]]:
    """Fetch a single row from a query."""
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    return dict(row) if row else None
