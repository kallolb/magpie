"""Tests for the /api/tags endpoints."""

import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport

from app.config import Settings
from app.database import init_db, get_db_dep


@pytest_asyncio.fixture
async def client(tmp_storage):
    settings = Settings(STORAGE_ROOT=str(tmp_storage), API_KEY="test-key")
    await init_db(settings.DATABASE_PATH)

    from app.main import create_app
    from app.config import get_settings

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    async def override_db():
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            yield db

    app.dependency_overrides[get_db_dep] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestListTags:
    async def test_empty_tags(self, client):
        resp = await client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_lists_created_tags(self, client):
        await client.post("/api/tags", json={"name": "python"})
        await client.post("/api/tags", json={"name": "javascript"})
        resp = await client.get("/api/tags")
        data = resp.json()
        assert len(data) == 2
        names = {t["name"] for t in data}
        assert names == {"python", "javascript"}

    async def test_tag_includes_video_count(self, client):
        resp = await client.post("/api/tags", json={"name": "test-tag"})
        data = resp.json()
        assert data["video_count"] == 0


@pytest.mark.asyncio
class TestCreateTag:
    async def test_create_tag(self, client):
        resp = await client.post("/api/tags", json={"name": "my-tag"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-tag"
        assert "id" in data

    async def test_duplicate_tag_returns_409(self, client):
        await client.post("/api/tags", json={"name": "duplicate"})
        resp = await client.post("/api/tags", json={"name": "duplicate"})
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestDeleteTag:
    async def test_delete_tag(self, client):
        create_resp = await client.post("/api/tags", json={"name": "to-delete"})
        tag_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/tags/{tag_id}")
        assert resp.status_code == 204

        list_resp = await client.get("/api/tags")
        names = {t["name"] for t in list_resp.json()}
        assert "to-delete" not in names

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/tags/99999")
        assert resp.status_code == 404
