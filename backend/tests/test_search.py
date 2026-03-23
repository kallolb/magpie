"""Tests for app.services.search."""

import pytest
import pytest_asyncio
import aiosqlite

from app.services.search import search_videos, rebuild_fts_tags


@pytest.mark.asyncio
class TestSearchVideos:
    """Tests for search_videos()."""

    async def test_search_by_title(self, db_with_videos):
        videos, total = await search_videos(db_with_videos, query="Python")
        assert total >= 1
        assert any("Python" in v["title"] for v in videos)

    async def test_search_by_uploader(self, db_with_videos):
        videos, total = await search_videos(db_with_videos, query="CodeChannel")
        assert total >= 1

    async def test_search_by_tag(self, db_with_videos):
        videos, total = await search_videos(db_with_videos, query="python")
        assert total >= 1
        titles = [v["title"] for v in videos]
        assert "Python Tutorial for Beginners" in titles

    async def test_search_no_results(self, db_with_videos):
        videos, total = await search_videos(db_with_videos, query="nonexistentxyz123")
        assert total == 0
        assert videos == []

    async def test_search_with_category_filter(self, db_with_videos):
        videos, total = await search_videos(
            db_with_videos, query="Python", category="tutorials"
        )
        assert total >= 1
        for v in videos:
            assert v["category"] == "tutorials"

    async def test_search_with_wrong_category_returns_empty(self, db_with_videos):
        videos, total = await search_videos(
            db_with_videos, query="Python", category="gaming"
        )
        assert total == 0

    async def test_search_with_tag_filter(self, db_with_videos):
        videos, total = await search_videos(
            db_with_videos, query="Tutorial", tags=["python"]
        )
        assert total >= 1

    async def test_search_pagination(self, db_with_videos):
        videos_p1, total = await search_videos(
            db_with_videos, query="Learning OR Tutorial OR Gaming OR News OR cooking", page=1, per_page=2
        )
        assert len(videos_p1) <= 2
        assert total >= 2

    async def test_search_returns_tags(self, db_with_videos):
        videos, total = await search_videos(db_with_videos, query="Python")
        assert total >= 1
        video = next(v for v in videos if v["title"] == "Python Tutorial for Beginners")
        assert "python" in video["tags"]
        assert "beginner" in video["tags"]

    async def test_search_case_insensitive(self, db_with_videos):
        videos_lower, total_lower = await search_videos(db_with_videos, query="python")
        videos_upper, total_upper = await search_videos(db_with_videos, query="Python")
        assert total_lower == total_upper


@pytest.mark.asyncio
class TestRebuildFtsTags:
    """Tests for rebuild_fts_tags()."""

    async def test_rebuild_updates_fts_index(self, db_with_videos):
        db = db_with_videos
        # Add a new tag to vid-2
        await db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", ("esports",))
        await db.commit()
        cursor = await db.execute("SELECT id FROM tags WHERE name = ?", ("esports",))
        tag_row = await cursor.fetchone()
        await db.execute(
            "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)",
            ("vid-2", tag_row[0]),
        )
        await db.commit()

        # Rebuild FTS
        await rebuild_fts_tags(db, "vid-2")

        # Now search for "esports" should find vid-2
        videos, total = await search_videos(db, query="esports")
        assert total >= 1
        assert any(v["title"] == "Epic Gaming Montage" for v in videos)

    async def test_rebuild_nonexistent_video_does_not_raise(self, db_with_videos):
        # Should silently do nothing
        await rebuild_fts_tags(db_with_videos, "nonexistent-id")
