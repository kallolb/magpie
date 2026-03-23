"""Tests for app.database initialization and helpers."""

import pytest
import pytest_asyncio
import aiosqlite

from app.database import init_db, fetch_all, fetch_one, execute_query


@pytest.mark.asyncio
class TestInitDb:
    """Tests for database initialization."""

    async def test_creates_videos_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='videos'"
        )
        row = await cursor.fetchone()
        assert row is not None

    async def test_creates_tags_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tags'"
        )
        assert await cursor.fetchone() is not None

    async def test_creates_video_tags_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='video_tags'"
        )
        assert await cursor.fetchone() is not None

    async def test_creates_categories_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='categories'"
        )
        assert await cursor.fetchone() is not None

    async def test_creates_fts_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='videos_fts'"
        )
        assert await cursor.fetchone() is not None

    async def test_creates_download_log_table(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='download_log'"
        )
        assert await cursor.fetchone() is not None

    async def test_default_categories_created(self, db):
        cursor = await db.execute("SELECT COUNT(*) FROM categories")
        row = await cursor.fetchone()
        assert row[0] == 10  # 10 default categories

    async def test_uncategorized_exists(self, db):
        cursor = await db.execute(
            "SELECT name FROM categories WHERE name = 'uncategorized'"
        )
        assert await cursor.fetchone() is not None

    async def test_idempotent_initialization(self, settings):
        # Calling init_db twice should not raise
        await init_db(settings.DATABASE_PATH)
        await init_db(settings.DATABASE_PATH)

    async def test_indexes_created(self, db):
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )
        indexes = [row[0] for row in await cursor.fetchall()]
        assert "idx_videos_platform_id" in indexes
        assert "idx_videos_category" in indexes
        assert "idx_videos_status" in indexes
        assert "idx_videos_created_at" in indexes
        assert "idx_video_tags_tag_id" in indexes
        assert "idx_download_log_video_id" in indexes


@pytest.mark.asyncio
class TestDatabaseHelpers:
    """Tests for database query helper functions."""

    async def test_fetch_all(self, db):
        rows = await fetch_all(db, "SELECT name FROM categories ORDER BY name LIMIT 3")
        assert len(rows) == 3
        assert all("name" in row for row in rows)

    async def test_fetch_all_with_params(self, db):
        rows = await fetch_all(
            db, "SELECT name FROM categories WHERE name = ?", ("music",)
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "music"

    async def test_fetch_one(self, db):
        row = await fetch_one(
            db, "SELECT name FROM categories WHERE name = ?", ("tech",)
        )
        assert row is not None
        assert row["name"] == "tech"

    async def test_fetch_one_no_match(self, db):
        row = await fetch_one(
            db, "SELECT name FROM categories WHERE name = ?", ("nonexistent",)
        )
        assert row is None

    async def test_execute_query(self, db):
        await execute_query(
            db,
            "INSERT INTO tags (name) VALUES (?)",
            ("test-tag",),
        )
        cursor = await db.execute("SELECT name FROM tags WHERE name = ?", ("test-tag",))
        row = await cursor.fetchone()
        assert row is not None
