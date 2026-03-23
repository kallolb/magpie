"""Tests for the /api/categories endpoints."""

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
class TestListCategories:
    async def test_lists_default_categories(self, client):
        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 10
        names = {c["name"] for c in data}
        assert "uncategorized" in names
        assert "music" in names
        assert "tutorials" in names

    async def test_categories_include_video_count(self, client):
        resp = await client.get("/api/categories")
        for cat in resp.json():
            assert "video_count" in cat


@pytest.mark.asyncio
class TestCreateCategory:
    async def test_create_category(self, client):
        resp = await client.post(
            "/api/categories",
            json={"name": "custom-cat", "description": "My custom category"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "custom-cat"
        assert data["description"] == "My custom category"

    async def test_duplicate_category_returns_409(self, client):
        await client.post("/api/categories", json={"name": "new-cat"})
        resp = await client.post("/api/categories", json={"name": "new-cat"})
        assert resp.status_code == 409


@pytest.mark.asyncio
class TestDeleteCategory:
    async def test_delete_custom_category(self, client):
        await client.post("/api/categories", json={"name": "deletable"})
        resp = await client.delete("/api/categories/deletable")
        assert resp.status_code == 204

    async def test_cannot_delete_uncategorized(self, client):
        resp = await client.delete("/api/categories/uncategorized")
        assert resp.status_code == 400

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/categories/nonexistent")
        assert resp.status_code == 404
