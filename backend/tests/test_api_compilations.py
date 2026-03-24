"""Tests for the /api/compilations endpoints."""

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
        # Seed two videos
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            for vid_id, title in [("vid-1", "Video One"), ("vid-2", "Video Two")]:
                await db.execute(
                    """INSERT INTO videos
                       (id, source_url, platform, title, category, status, progress, file_path)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (vid_id, f"https://example.com/{vid_id}", "youtube", title,
                     "tutorials", "completed", 100.0, f"categories/tutorials/{vid_id}.mp4"),
                )
            # Add a loop marker on vid-1
            await db.execute(
                "INSERT INTO loop_markers (video_id, label, start_secs, end_secs) VALUES (?, ?, ?, ?)",
                ("vid-1", "Chorus", 10.0, 25.0),
            )
            await db.commit()
        yield ac


@pytest.mark.asyncio
class TestCompilationCRUD:
    async def test_create(self, client):
        resp = await client.post("/api/compilations", json={"title": "My Compilation"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My Compilation"
        assert data["status"] == "draft"
        assert data["clip_count"] == 0
        assert "id" in data

    async def test_list_empty(self, client):
        resp = await client.get("/api/compilations")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_returns_created(self, client):
        await client.post("/api/compilations", json={"title": "A"})
        await client.post("/api/compilations", json={"title": "B"})
        resp = await client.get("/api/compilations")
        assert len(resp.json()) == 2

    async def test_get_by_id(self, client):
        create_resp = await client.post("/api/compilations", json={"title": "Test"})
        comp_id = create_resp.json()["id"]
        resp = await client.get(f"/api/compilations/{comp_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test"

    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/compilations/no-such-id")
        assert resp.status_code == 404

    async def test_update_title(self, client):
        create_resp = await client.post("/api/compilations", json={"title": "Old"})
        comp_id = create_resp.json()["id"]
        resp = await client.put(f"/api/compilations/{comp_id}", json={"title": "New"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New"

    async def test_delete(self, client):
        create_resp = await client.post("/api/compilations", json={"title": "Delete Me"})
        comp_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/compilations/{comp_id}")
        assert resp.status_code == 204
        list_resp = await client.get("/api/compilations")
        assert len(list_resp.json()) == 0

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/compilations/no-such-id")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestClipManagement:
    async def _create_compilation(self, client) -> str:
        resp = await client.post("/api/compilations", json={"title": "Test Comp"})
        return resp.json()["id"]

    async def test_add_clip(self, client):
        comp_id = await self._create_compilation(client)
        resp = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 5.0, "end_secs": 15.0, "label": "Intro",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_video_id"] == "vid-1"
        assert data["position"] == 1
        assert data["label"] == "Intro"
        assert data["duration_secs"] == 10.0
        assert data["source_video_title"] == "Video One"

    async def test_add_clip_invalid_times(self, client):
        comp_id = await self._create_compilation(client)
        resp = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 20.0, "end_secs": 10.0,
        })
        assert resp.status_code == 400

    async def test_add_clip_nonexistent_video(self, client):
        comp_id = await self._create_compilation(client)
        resp = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "no-video", "start_secs": 0.0, "end_secs": 5.0,
        })
        assert resp.status_code == 404

    async def test_auto_position(self, client):
        comp_id = await self._create_compilation(client)
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 5.0,
        })
        resp = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-2", "start_secs": 10.0, "end_secs": 20.0,
        })
        assert resp.json()["position"] == 2

    async def test_update_clip(self, client):
        comp_id = await self._create_compilation(client)
        clip_resp = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 10.0, "label": "Old",
        })
        clip_id = clip_resp.json()["id"]
        resp = await client.put(f"/api/compilations/{comp_id}/clips/{clip_id}", json={
            "label": "New Label", "start_secs": 2.0,
        })
        assert resp.status_code == 200
        assert resp.json()["label"] == "New Label"
        assert resp.json()["start_secs"] == 2.0
        assert resp.json()["end_secs"] == 10.0

    async def test_delete_clip_reorders(self, client):
        comp_id = await self._create_compilation(client)
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 5.0, "label": "A",
        })
        clip2 = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 5.0, "end_secs": 10.0, "label": "B",
        })
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-2", "start_secs": 0.0, "end_secs": 5.0, "label": "C",
        })

        # Delete clip B (position 2)
        await client.delete(f"/api/compilations/{comp_id}/clips/{clip2.json()['id']}")

        comp = await client.get(f"/api/compilations/{comp_id}")
        clips = comp.json()["clips"]
        assert len(clips) == 2
        assert clips[0]["label"] == "A"
        assert clips[0]["position"] == 1
        assert clips[1]["label"] == "C"
        assert clips[1]["position"] == 2

    async def test_reorder_clips(self, client):
        comp_id = await self._create_compilation(client)
        c1 = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 5.0, "label": "First",
        })
        c2 = await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-2", "start_secs": 0.0, "end_secs": 5.0, "label": "Second",
        })

        resp = await client.put(f"/api/compilations/{comp_id}/clips/reorder", json={
            "clip_ids": [c2.json()["id"], c1.json()["id"]],
        })
        assert resp.status_code == 200
        clips = resp.json()
        assert clips[0]["label"] == "Second"
        assert clips[0]["position"] == 1
        assert clips[1]["label"] == "First"
        assert clips[1]["position"] == 2

    async def test_reorder_wrong_ids(self, client):
        comp_id = await self._create_compilation(client)
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 5.0,
        })
        resp = await client.put(f"/api/compilations/{comp_id}/clips/reorder", json={
            "clip_ids": [999],
        })
        assert resp.status_code == 400


@pytest.mark.asyncio
class TestLoopImport:
    async def test_import_loop_as_clip(self, client):
        comp_resp = await client.post("/api/compilations", json={"title": "Loop Test"})
        comp_id = comp_resp.json()["id"]

        # Loop marker id=1 was seeded in fixture
        resp = await client.post(f"/api/compilations/{comp_id}/clips/from-loop/1")
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_video_id"] == "vid-1"
        assert data["start_secs"] == 10.0
        assert data["end_secs"] == 25.0
        assert data["label"] == "Chorus"

    async def test_import_nonexistent_loop(self, client):
        comp_resp = await client.post("/api/compilations", json={"title": "Test"})
        comp_id = comp_resp.json()["id"]
        resp = await client.post(f"/api/compilations/{comp_id}/clips/from-loop/999")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestCompilationCascade:
    async def test_clips_deleted_with_compilation(self, client):
        comp_resp = await client.post("/api/compilations", json={"title": "Cascade Test"})
        comp_id = comp_resp.json()["id"]
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 5.0,
        })
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-2", "start_secs": 0.0, "end_secs": 5.0,
        })

        resp = await client.delete(f"/api/compilations/{comp_id}")
        assert resp.status_code == 204

    async def test_estimated_duration(self, client):
        comp_resp = await client.post("/api/compilations", json={"title": "Duration Test"})
        comp_id = comp_resp.json()["id"]
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-1", "start_secs": 0.0, "end_secs": 10.0,
        })
        await client.post(f"/api/compilations/{comp_id}/clips", json={
            "source_video_id": "vid-2", "start_secs": 5.0, "end_secs": 20.0,
        })
        resp = await client.get(f"/api/compilations/{comp_id}")
        assert resp.json()["estimated_duration_secs"] == 25.0
        assert resp.json()["clip_count"] == 2
