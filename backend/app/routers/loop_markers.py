from typing import Any

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db_dep
from app.models.loop_marker import LoopMarkerCreate, LoopMarkerResponse, LoopMarkerUpdate

logger = structlog.get_logger()

router = APIRouter(prefix="/api/videos", tags=["loop-markers"])


@router.get("/{video_id}/loops", response_model=list[LoopMarkerResponse])
async def list_loop_markers(
    video_id: str,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> list[LoopMarkerResponse]:
    """List all loop markers for a video."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT id, video_id, label, start_secs, end_secs, created_at FROM loop_markers WHERE video_id = ? ORDER BY start_secs",
        (video_id,),
    )
    rows = await cursor.fetchall()
    return [LoopMarkerResponse(**dict(row)) for row in rows]


@router.post("/{video_id}/loops", response_model=LoopMarkerResponse, status_code=status.HTTP_201_CREATED)
async def create_loop_marker(
    video_id: str,
    marker: LoopMarkerCreate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> LoopMarkerResponse:
    """Create a loop marker for a video."""
    db.row_factory = aiosqlite.Row

    # Verify video exists
    cursor = await db.execute("SELECT id FROM videos WHERE id = ?", (video_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if marker.start_secs >= marker.end_secs:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_secs must be less than end_secs")

    cursor = await db.execute(
        "INSERT INTO loop_markers (video_id, label, start_secs, end_secs) VALUES (?, ?, ?, ?)",
        (video_id, marker.label, marker.start_secs, marker.end_secs),
    )
    await db.commit()

    row_id = cursor.lastrowid
    cursor = await db.execute(
        "SELECT id, video_id, label, start_secs, end_secs, created_at FROM loop_markers WHERE id = ?",
        (row_id,),
    )
    row = await cursor.fetchone()
    logger.info("loop_marker_created", video_id=video_id, marker_id=row_id)
    return LoopMarkerResponse(**dict(row))


@router.put("/{video_id}/loops/{loop_id}", response_model=LoopMarkerResponse)
async def update_loop_marker(
    video_id: str,
    loop_id: int,
    update: LoopMarkerUpdate,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> LoopMarkerResponse:
    """Rename a loop marker."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT id FROM loop_markers WHERE id = ? AND video_id = ?",
        (loop_id, video_id),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop marker not found")

    await db.execute("UPDATE loop_markers SET label = ? WHERE id = ?", (update.label, loop_id))
    await db.commit()

    cursor = await db.execute(
        "SELECT id, video_id, label, start_secs, end_secs, created_at FROM loop_markers WHERE id = ?",
        (loop_id,),
    )
    row = await cursor.fetchone()
    logger.info("loop_marker_renamed", video_id=video_id, marker_id=loop_id, label=update.label)
    return LoopMarkerResponse(**dict(row))


@router.delete("/{video_id}/loops/{loop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loop_marker(
    video_id: str,
    loop_id: int,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    """Delete a loop marker."""
    cursor = await db.execute(
        "SELECT id FROM loop_markers WHERE id = ? AND video_id = ?",
        (loop_id, video_id),
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop marker not found")

    await db.execute("DELETE FROM loop_markers WHERE id = ?", (loop_id,))
    await db.commit()
    logger.info("loop_marker_deleted", video_id=video_id, marker_id=loop_id)
