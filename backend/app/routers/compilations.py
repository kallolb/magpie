import asyncio
import uuid
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.services.renderer import analyze_clips, render_compilation
from app.models.compilation import (
    ClipCreate,
    ClipReorder,
    ClipResponse,
    ClipUpdate,
    CompilationCreate,
    CompilationResponse,
    CompilationUpdate,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/compilations", tags=["compilations"])


async def _get_clips(db: aiosqlite.Connection, compilation_id: str) -> list[ClipResponse]:
    """Fetch all clips for a compilation with source video info."""
    cursor = await db.execute(
        """SELECT cc.id, cc.compilation_id, cc.source_video_id, cc.position,
                  cc.start_secs, cc.end_secs, cc.label, cc.created_at,
                  v.title as source_video_title, v.thumbnail_path as source_video_thumbnail
           FROM compilation_clips cc
           LEFT JOIN videos v ON cc.source_video_id = v.id
           WHERE cc.compilation_id = ?
           ORDER BY cc.position""",
        (compilation_id,),
    )
    rows = await cursor.fetchall()
    clips = []
    for row in rows:
        d = dict(row)
        thumb = d.get("source_video_thumbnail")
        if thumb and not thumb.startswith("/"):
            d["source_video_thumbnail"] = f"/api/{thumb}"
        d["duration_secs"] = round(d["end_secs"] - d["start_secs"], 2)
        clips.append(ClipResponse(**d))
    return clips


async def _build_response(db: aiosqlite.Connection, compilation_id: str) -> CompilationResponse:
    """Build a full CompilationResponse with clips."""
    cursor = await db.execute(
        """SELECT id, title, description, category, status, render_mode,
                  output_path, output_size_bytes, duration_secs, thumbnail_path,
                  error_message, created_at, updated_at
           FROM compilations WHERE id = ?""",
        (compilation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")

    data = dict(row)
    clips = await _get_clips(db, compilation_id)
    data["clips"] = clips
    data["clip_count"] = len(clips)
    data["estimated_duration_secs"] = round(sum(c.duration_secs for c in clips), 2)
    return CompilationResponse(**data)


# --- Compilation CRUD ---


@router.post("", response_model=CompilationResponse, status_code=status.HTTP_201_CREATED)
async def create_compilation(
    body: CompilationCreate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> CompilationResponse:
    comp_id = str(uuid.uuid4())
    db.row_factory = aiosqlite.Row
    await db.execute(
        "INSERT INTO compilations (id, title, description, category) VALUES (?, ?, ?, ?)",
        (comp_id, body.title, body.description, body.category),
    )
    await db.commit()
    logger.info("compilation_created", compilation_id=comp_id)
    return await _build_response(db, comp_id)


@router.get("", response_model=list[CompilationResponse])
async def list_compilations(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> list[CompilationResponse]:
    db.row_factory = aiosqlite.Row
    sql = "SELECT id FROM compilations WHERE 1=1"
    params: list[Any] = []
    if status_filter:
        sql += " AND status = ?"
        params.append(status_filter)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like])
    sql += " ORDER BY updated_at DESC"

    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return [await _build_response(db, row["id"]) for row in rows]


@router.get("/{compilation_id}", response_model=CompilationResponse)
async def get_compilation(
    compilation_id: str,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> CompilationResponse:
    db.row_factory = aiosqlite.Row
    return await _build_response(db, compilation_id)


@router.put("/{compilation_id}", response_model=CompilationResponse)
async def update_compilation(
    compilation_id: str,
    body: CompilationUpdate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> CompilationResponse:
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT id FROM compilations WHERE id = ?", (compilation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")

    if body.title is not None:
        await db.execute(
            "UPDATE compilations SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (body.title, compilation_id),
        )
    if body.description is not None:
        await db.execute(
            "UPDATE compilations SET description = ?, updated_at = datetime('now') WHERE id = ?",
            (body.description, compilation_id),
        )
    if body.category is not None:
        await db.execute(
            "UPDATE compilations SET category = ?, updated_at = datetime('now') WHERE id = ?",
            (body.category, compilation_id),
        )
    await db.commit()
    logger.info("compilation_updated", compilation_id=compilation_id)
    return await _build_response(db, compilation_id)


@router.delete("/{compilation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compilation(
    compilation_id: str,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    db.row_factory = aiosqlite.Row
    cursor = await db.execute("SELECT id FROM compilations WHERE id = ?", (compilation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")

    await db.execute("DELETE FROM compilations WHERE id = ?", (compilation_id,))
    await db.commit()
    logger.info("compilation_deleted", compilation_id=compilation_id)


# --- Clip Management ---


@router.post("/{compilation_id}/clips", response_model=ClipResponse, status_code=status.HTTP_201_CREATED)
async def add_clip(
    compilation_id: str,
    body: ClipCreate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> ClipResponse:
    db.row_factory = aiosqlite.Row

    # Verify compilation exists and is in draft
    cursor = await db.execute("SELECT status FROM compilations WHERE id = ?", (compilation_id,))
    comp = await cursor.fetchone()
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")
    if comp["status"] not in ("draft", "failed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a compilation that is rendering or completed")

    # Verify source video exists
    cursor = await db.execute("SELECT id FROM videos WHERE id = ?", (body.source_video_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source video not found")

    if body.start_secs >= body.end_secs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_secs must be less than end_secs")

    # Get next position
    cursor = await db.execute(
        "SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM compilation_clips WHERE compilation_id = ?",
        (compilation_id,),
    )
    next_pos = (await cursor.fetchone())["next_pos"]

    cursor = await db.execute(
        """INSERT INTO compilation_clips (compilation_id, source_video_id, position, start_secs, end_secs, label)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (compilation_id, body.source_video_id, next_pos, body.start_secs, body.end_secs, body.label),
    )
    await db.execute("UPDATE compilations SET updated_at = datetime('now') WHERE id = ?", (compilation_id,))
    await db.commit()

    clip_id = cursor.lastrowid
    cursor = await db.execute(
        """SELECT cc.id, cc.compilation_id, cc.source_video_id, cc.position,
                  cc.start_secs, cc.end_secs, cc.label, cc.created_at,
                  v.title as source_video_title, v.thumbnail_path as source_video_thumbnail
           FROM compilation_clips cc
           LEFT JOIN videos v ON cc.source_video_id = v.id
           WHERE cc.id = ?""",
        (clip_id,),
    )
    row = await cursor.fetchone()
    d = dict(row)
    thumb = d.get("source_video_thumbnail")
    if thumb and not thumb.startswith("/"):
        d["source_video_thumbnail"] = f"/api/{thumb}"
    d["duration_secs"] = round(d["end_secs"] - d["start_secs"], 2)
    logger.info("clip_added", compilation_id=compilation_id, clip_id=clip_id)
    return ClipResponse(**d)


@router.put("/{compilation_id}/clips/reorder", response_model=list[ClipResponse])
async def reorder_clips(
    compilation_id: str,
    body: ClipReorder,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> list[ClipResponse]:
    db.row_factory = aiosqlite.Row

    cursor = await db.execute("SELECT id FROM compilations WHERE id = ?", (compilation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")

    # Verify all clip IDs belong to this compilation
    cursor = await db.execute(
        "SELECT id FROM compilation_clips WHERE compilation_id = ?", (compilation_id,)
    )
    existing_ids = {row["id"] for row in await cursor.fetchall()}
    if set(body.clip_ids) != existing_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="clip_ids must contain exactly all clips in this compilation")

    for position, clip_id in enumerate(body.clip_ids, start=1):
        await db.execute(
            "UPDATE compilation_clips SET position = ? WHERE id = ? AND compilation_id = ?",
            (position, clip_id, compilation_id),
        )
    await db.execute("UPDATE compilations SET updated_at = datetime('now') WHERE id = ?", (compilation_id,))
    await db.commit()
    logger.info("clips_reordered", compilation_id=compilation_id)
    return await _get_clips(db, compilation_id)


@router.put("/{compilation_id}/clips/{clip_id}", response_model=ClipResponse)
async def update_clip(
    compilation_id: str,
    clip_id: int,
    body: ClipUpdate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> ClipResponse:
    db.row_factory = aiosqlite.Row

    cursor = await db.execute(
        "SELECT id, start_secs, end_secs FROM compilation_clips WHERE id = ? AND compilation_id = ?",
        (clip_id, compilation_id),
    )
    existing = await cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")

    start = body.start_secs if body.start_secs is not None else existing["start_secs"]
    end = body.end_secs if body.end_secs is not None else existing["end_secs"]
    if start >= end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_secs must be less than end_secs")

    updates = []
    params: list[Any] = []
    if body.start_secs is not None:
        updates.append("start_secs = ?")
        params.append(body.start_secs)
    if body.end_secs is not None:
        updates.append("end_secs = ?")
        params.append(body.end_secs)
    if body.label is not None:
        updates.append("label = ?")
        params.append(body.label)

    if updates:
        params.append(clip_id)
        await db.execute(f"UPDATE compilation_clips SET {', '.join(updates)} WHERE id = ?", params)
        await db.execute("UPDATE compilations SET updated_at = datetime('now') WHERE id = ?", (compilation_id,))
        await db.commit()

    # Refetch
    cursor = await db.execute(
        """SELECT cc.id, cc.compilation_id, cc.source_video_id, cc.position,
                  cc.start_secs, cc.end_secs, cc.label, cc.created_at,
                  v.title as source_video_title, v.thumbnail_path as source_video_thumbnail
           FROM compilation_clips cc
           LEFT JOIN videos v ON cc.source_video_id = v.id
           WHERE cc.id = ?""",
        (clip_id,),
    )
    row = await cursor.fetchone()
    d = dict(row)
    thumb = d.get("source_video_thumbnail")
    if thumb and not thumb.startswith("/"):
        d["source_video_thumbnail"] = f"/api/{thumb}"
    d["duration_secs"] = round(d["end_secs"] - d["start_secs"], 2)
    return ClipResponse(**d)


@router.delete("/{compilation_id}/clips/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    compilation_id: str,
    clip_id: int,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    db.row_factory = aiosqlite.Row

    cursor = await db.execute(
        "SELECT position FROM compilation_clips WHERE id = ? AND compilation_id = ?",
        (clip_id, compilation_id),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found")

    deleted_pos = row["position"]
    await db.execute("DELETE FROM compilation_clips WHERE id = ?", (clip_id,))
    # Reorder remaining clips
    await db.execute(
        "UPDATE compilation_clips SET position = position - 1 WHERE compilation_id = ? AND position > ?",
        (compilation_id, deleted_pos),
    )
    await db.execute("UPDATE compilations SET updated_at = datetime('now') WHERE id = ?", (compilation_id,))
    await db.commit()
    logger.info("clip_deleted", compilation_id=compilation_id, clip_id=clip_id)


@router.post("/{compilation_id}/clips/from-loop/{loop_id}", response_model=ClipResponse, status_code=status.HTTP_201_CREATED)
async def import_from_loop(
    compilation_id: str,
    loop_id: int,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> ClipResponse:
    """Import a loop marker as a clip."""
    db.row_factory = aiosqlite.Row

    cursor = await db.execute("SELECT status FROM compilations WHERE id = ?", (compilation_id,))
    comp = await cursor.fetchone()
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")
    if comp["status"] not in ("draft", "failed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a compilation that is rendering or completed")

    cursor = await db.execute(
        "SELECT video_id, label, start_secs, end_secs FROM loop_markers WHERE id = ?", (loop_id,)
    )
    loop = await cursor.fetchone()
    if not loop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop marker not found")

    # Delegate to add_clip logic
    clip_body = ClipCreate(
        source_video_id=loop["video_id"],
        start_secs=loop["start_secs"],
        end_secs=loop["end_secs"],
        label=loop["label"],
    )
    return await add_clip(compilation_id, clip_body, db)


# --- Render Pipeline ---

class RenderRequest(BaseModel):
    mode: str = "auto"  # "copy", "reencode", or "auto"


@router.post("/{compilation_id}/analyze")
async def analyze_compilation(
    compilation_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, Any]:
    """Analyze clips for codec compatibility."""
    db.row_factory = aiosqlite.Row

    cursor = await db.execute("SELECT id FROM compilations WHERE id = ?", (compilation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")

    cursor = await db.execute(
        """SELECT cc.id as clip_id, cc.source_video_id, cc.start_secs, cc.end_secs,
                  v.file_path
           FROM compilation_clips cc
           JOIN videos v ON cc.source_video_id = v.id
           WHERE cc.compilation_id = ?
           ORDER BY cc.position""",
        (compilation_id,),
    )
    clips = [dict(r) for r in await cursor.fetchall()]

    if not clips:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No clips to analyze")

    for clip in clips:
        clip["duration"] = clip["end_secs"] - clip["start_secs"]

    return await analyze_clips(clips, settings.STORAGE_ROOT)


# In-memory render tasks
_render_tasks: dict[str, asyncio.Task[None]] = {}


@router.post("/{compilation_id}/render")
async def start_render(
    compilation_id: str,
    body: RenderRequest,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, str]:
    """Start rendering a compilation."""
    db.row_factory = aiosqlite.Row

    cursor = await db.execute("SELECT status FROM compilations WHERE id = ?", (compilation_id,))
    comp = await cursor.fetchone()
    if not comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")
    if comp["status"] == "rendering":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already rendering")

    # Check clips exist
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM compilation_clips WHERE compilation_id = ?", (compilation_id,)
    )
    if (await cursor.fetchone())["cnt"] == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No clips to render")

    # Determine mode
    mode = body.mode
    if mode == "auto":
        # Analyze and pick recommendation
        cursor = await db.execute(
            """SELECT cc.id as clip_id, cc.source_video_id, cc.start_secs, cc.end_secs, v.file_path
               FROM compilation_clips cc JOIN videos v ON cc.source_video_id = v.id
               WHERE cc.compilation_id = ? ORDER BY cc.position""",
            (compilation_id,),
        )
        clips = [dict(r) for r in await cursor.fetchall()]
        for c in clips:
            c["duration"] = c["end_secs"] - c["start_secs"]
        analysis = await analyze_clips(clips, settings.STORAGE_ROOT)
        mode = analysis["recommendation"]

    # Launch background task
    task = asyncio.create_task(
        render_compilation(settings.DATABASE_PATH, settings.STORAGE_ROOT, compilation_id, mode)
    )
    _render_tasks[compilation_id] = task

    logger.info("render_started", compilation_id=compilation_id, mode=mode)
    return {"status": "rendering", "mode": mode}


@router.get("/{compilation_id}/render/progress")
async def render_progress(
    compilation_id: str,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """SSE stream for render progress."""
    async def event_generator():
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            db.row_factory = aiosqlite.Row

            last_status = None
            while True:
                cursor = await db.execute(
                    "SELECT status, error_message FROM compilations WHERE id = ?",
                    (compilation_id,),
                )
                row = await cursor.fetchone()
                if not row:
                    yield f'data: {{"status": "not_found"}}\n\n'
                    break

                current = row["status"]
                if current != last_status:
                    data = f'{{"status": "{current}"'
                    if row["error_message"]:
                        err = row["error_message"].replace('"', '\\"')
                        data += f', "error": "{err}"'
                    data += '}'
                    yield f'data: {data}\n\n'
                    last_status = current

                if current in ("completed", "failed"):
                    yield 'event: close\ndata: {}\n\n'
                    break

                await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{compilation_id}/stream")
async def stream_compilation(
    compilation_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> FileResponse:
    """Stream the rendered compilation file."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT output_path, status FROM compilations WHERE id = ?", (compilation_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compilation not found")
    if row["status"] != "completed" or not row["output_path"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Compilation not yet rendered")

    file_path = Path(settings.STORAGE_ROOT) / row["output_path"]
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output file not found")

    return FileResponse(path=file_path, media_type="video/mp4", filename=file_path.name)
