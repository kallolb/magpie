"""Tests for the /api/videos/{video_id}/loops endpoints."""

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
            await db.execute("PRAGMA foreign_keys = ON")
            db.row_factory = aiosqlite.Row
            yield db

    app.dependency_overrides[get_db_dep] = override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Seed a video for loop marker tests
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            await db.execute(
                """INSERT INTO videos
                   (id, source_url, platform, title, category, status, progress)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("vid-1", "https://youtube.com/watch?v=abc", "youtube",
                 "Test Video", "tutorials", "completed", 100.0),
            )
            await db.commit()
        yield ac


@pytest.mark.asyncio
class TestListLoopMarkers:
    async def test_empty_list(self, client):
        resp = await client.get("/api/videos/vid-1/loops")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_created_markers(self, client):
        await client.post("/api/videos/vid-1/loops", json={
            "label": "Chorus", "start_secs": 10.0, "end_secs": 30.0,
        })
        await client.post("/api/videos/vid-1/loops", json={
            "label": "Verse", "start_secs": 0.0, "end_secs": 10.0,
        })
        resp = await client.get("/api/videos/vid-1/loops")
        data = resp.json()
        assert len(data) == 2
        # Should be ordered by start_secs
        assert data[0]["label"] == "Verse"
        assert data[1]["label"] == "Chorus"


@pytest.mark.asyncio
class TestCreateLoopMarker:
    async def test_create_marker(self, client):
        resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Bridge", "start_secs": 45.5, "end_secs": 78.2,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Bridge"
        assert data["start_secs"] == 45.5
        assert data["end_secs"] == 78.2
        assert data["video_id"] == "vid-1"
        assert "id" in data
        assert "created_at" in data

    async def test_create_for_nonexistent_video(self, client):
        resp = await client.post("/api/videos/no-such-video/loops", json={
            "label": "Test", "start_secs": 0.0, "end_secs": 5.0,
        })
        assert resp.status_code == 404

    async def test_start_must_be_less_than_end(self, client):
        resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Bad", "start_secs": 30.0, "end_secs": 10.0,
        })
        assert resp.status_code == 400

    async def test_start_equals_end_rejected(self, client):
        resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Zero", "start_secs": 5.0, "end_secs": 5.0,
        })
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestUpdateLoopMarker:
    async def test_rename_marker(self, client):
        create_resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Original", "start_secs": 10.0, "end_secs": 20.0,
        })
        marker_id = create_resp.json()["id"]

        resp = await client.put(f"/api/videos/vid-1/loops/{marker_id}", json={
            "label": "Renamed",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["label"] == "Renamed"
        assert data["start_secs"] == 10.0
        assert data["end_secs"] == 20.0

    async def test_rename_nonexistent_marker(self, client):
        resp = await client.put("/api/videos/vid-1/loops/99999", json={
            "label": "Nope",
        })
        assert resp.status_code == 404

    async def test_rename_wrong_video_id(self, client):
        create_resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Mine", "start_secs": 1.0, "end_secs": 2.0,
        })
        marker_id = create_resp.json()["id"]

        resp = await client.put(f"/api/videos/wrong-video/loops/{marker_id}", json={
            "label": "Stolen",
        })
        assert resp.status_code == 404

    async def test_rename_persists(self, client):
        create_resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Before", "start_secs": 5.0, "end_secs": 15.0,
        })
        marker_id = create_resp.json()["id"]

        await client.put(f"/api/videos/vid-1/loops/{marker_id}", json={
            "label": "After",
        })

        list_resp = await client.get("/api/videos/vid-1/loops")
        labels = [m["label"] for m in list_resp.json()]
        assert "After" in labels
        assert "Before" not in labels


@pytest.mark.asyncio
class TestDeleteLoopMarker:
    async def test_delete_marker(self, client):
        create_resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "To Delete", "start_secs": 0.0, "end_secs": 5.0,
        })
        marker_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/videos/vid-1/loops/{marker_id}")
        assert resp.status_code == 204

        list_resp = await client.get("/api/videos/vid-1/loops")
        assert len(list_resp.json()) == 0

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/videos/vid-1/loops/99999")
        assert resp.status_code == 404

    async def test_delete_wrong_video_id(self, client):
        create_resp = await client.post("/api/videos/vid-1/loops", json={
            "label": "Owned", "start_secs": 1.0, "end_secs": 3.0,
        })
        marker_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/videos/wrong-video/loops/{marker_id}")
        assert resp.status_code == 404

        # Verify it still exists
        list_resp = await client.get("/api/videos/vid-1/loops")
        assert len(list_resp.json()) == 1


@pytest.mark.asyncio
class TestLoopMarkerCascadeDelete:
    async def test_loops_deleted_when_video_deleted(self, client):
        # Create some loops
        await client.post("/api/videos/vid-1/loops", json={
            "label": "A", "start_secs": 0.0, "end_secs": 5.0,
        })
        await client.post("/api/videos/vid-1/loops", json={
            "label": "B", "start_secs": 10.0, "end_secs": 20.0,
        })

        # Delete the video
        resp = await client.delete("/api/videos/vid-1")
        assert resp.status_code == 204

        # Loops should be gone too (video doesn't exist so 200 with empty list or 404)
        list_resp = await client.get("/api/videos/vid-1/loops")
        assert list_resp.status_code == 200
        assert list_resp.json() == []
