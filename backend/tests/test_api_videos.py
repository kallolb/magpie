"""Tests for the /api/videos endpoints."""

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

from app.config import Settings
from app.database import init_db, get_db_dep


@pytest_asyncio.fixture
async def app_and_settings(tmp_storage):
    """Create a test FastAPI app with isolated DB."""
    settings = Settings(STORAGE_ROOT=str(tmp_storage), API_KEY="test-key")
    await init_db(settings.DATABASE_PATH)

    from app.main import create_app
    from app.config import get_settings

    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings

    async def override_db():
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            yield db

    application.dependency_overrides[get_db_dep] = override_db
    return application, settings


@pytest_asyncio.fixture
async def client(app_and_settings):
    app, _ = app_and_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def client_with_videos(app_and_settings):
    app, settings = app_and_settings

    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO videos (id, source_url, platform, platform_id, title, category, status, progress)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("vid-1", "https://youtube.com/watch?v=abc", "youtube", "abc",
             "Test Video One", "tutorials", "completed", 100.0),
        )
        await db.execute(
            """INSERT INTO videos (id, source_url, platform, platform_id, title, category, status, progress)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("vid-2", "https://youtube.com/watch?v=def", "youtube", "def",
             "Test Video Two", "gaming", "completed", 100.0),
        )
        await db.execute("INSERT INTO tags (name) VALUES (?)", ("python",))
        await db.execute(
            "INSERT INTO video_tags (video_id, tag_id) VALUES (?, ?)", ("vid-1", 1)
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestListVideos:
    async def test_empty_list(self, client):
        resp = await client.get("/api/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_returns_videos(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_pagination(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos?page=1&per_page=1")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2

    async def test_filter_by_category(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos?category=tutorials")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "tutorials"

    async def test_filter_by_platform(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos?platform=youtube")
        data = resp.json()
        assert data["total"] == 2

    async def test_includes_tags(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos")
        data = resp.json()
        vid1 = next(v for v in data["items"] if v["id"] == "vid-1")
        assert "python" in vid1["tags"]


@pytest.mark.asyncio
class TestGetVideo:
    async def test_get_existing_video(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos/vid-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "vid-1"
        assert data["title"] == "Test Video One"

    async def test_get_nonexistent_video(self, client_with_videos):
        resp = await client_with_videos.get("/api/videos/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestUpdateVideo:
    async def test_update_title(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/vid-1", json={"title": "Updated Title"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    async def test_update_category(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/vid-1", json={"category": "tech"}
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "tech"

    async def test_update_tags(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/vid-1", json={"tags": ["new-tag", "another-tag"]}
        )
        assert resp.status_code == 200
        assert set(resp.json()["tags"]) == {"new-tag", "another-tag"}

    async def test_update_tags_creates_new_tags(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/vid-1", json={"tags": ["brand-new-tag"]}
        )
        assert resp.status_code == 200
        assert "brand-new-tag" in resp.json()["tags"]

    async def test_update_nonexistent_video(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/nonexistent", json={"title": "Nope"}
        )
        assert resp.status_code == 404

    async def test_update_rejects_extra_fields(self, client_with_videos):
        resp = await client_with_videos.put(
            "/api/videos/vid-1", json={"title": "OK", "nonexistent": "bad"}
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestDeleteVideo:
    async def test_delete_video(self, client_with_videos):
        resp = await client_with_videos.delete("/api/videos/vid-2")
        assert resp.status_code == 204

        resp = await client_with_videos.get("/api/videos/vid-2")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, client_with_videos):
        resp = await client_with_videos.delete("/api/videos/nonexistent")
        assert resp.status_code == 404
