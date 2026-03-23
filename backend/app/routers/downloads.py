import asyncio
import uuid
from typing import Any, Optional

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.models.video import DownloadRequest, DownloadStatus, VideoResponse
from app.services.notifier import NotificationManager
from app.tasks.download_task import process_download

logger = structlog.get_logger()

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

# In-memory task tracker (when Redis is not available)
active_tasks: dict[str, asyncio.Task[dict[str, Any]]] = {}
task_results: dict[str, dict[str, Any]] = {}

# Singleton notification manager
_notifier: Optional[NotificationManager] = None


def get_notifier() -> NotificationManager:
    """Get or create the notification manager."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
    return _notifier


async def _background_download(
    db_path: str,
    storage_root: str,
    video_id: str,
    url: str,
    category: Optional[str],
    tags: Optional[list[str]],
    quality: int,
    triggered_by: str,
) -> dict[str, Any]:
    """Background download task."""
    try:
        result = await process_download(
            db_path=db_path,
            storage_root=storage_root,
            video_id=video_id,
            url=url,
            category=category,
            tags=tags,
            quality=quality,
            triggered_by=triggered_by,
            notifier=get_notifier(),
        )
        task_results[video_id] = result
        return result
    finally:
        # Clean up task reference after a delay
        await asyncio.sleep(300)  # Keep for 5 minutes
        if video_id in active_tasks:
            del active_tasks[video_id]


@router.post("", response_model=dict[str, Any])
async def start_download(
    request: DownloadRequest,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, Any]:
    """Start a video download."""
    try:
        # Generate video ID
        video_id = str(uuid.uuid4())

        # Create initial record
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO videos (id, source_url, platform, title, status, category, progress)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                video_id,
                request.url,
                "unknown",
                "Processing...",
                "pending",
                request.category or "uncategorized",
                0,
            ),
        )
        await db.commit()

        # Start background task
        task = asyncio.create_task(
            _background_download(
                db_path=settings.DATABASE_PATH,
                storage_root=settings.STORAGE_ROOT,
                video_id=video_id,
                url=request.url,
                category=request.category,
                tags=request.tags,
                quality=request.quality or settings.DEFAULT_QUALITY,
                triggered_by="api",
            )
        )
        active_tasks[video_id] = task

        logger.info("download_started", video_id=video_id, url=request.url)

        return {
            "id": video_id,
            "status": "queued",
            "message": "Download queued successfully",
        }

    except Exception as e:
        logger.error("download_start_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{video_id}", response_model=DownloadStatus)
async def get_download_status(
    video_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> DownloadStatus:
    """Get the status of a download."""
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, source_url, platform, platform_id, title, description,
                   uploader, upload_date, duration_secs, resolution, file_path,
                   file_size_bytes, thumbnail_path, category, status,
                   error_message, progress, created_at, updated_at
            FROM videos WHERE id = ?
        """,
            (video_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download not found",
            )

        video_data = dict(row)

        # Get tags
        tags_cursor = await db.execute(
            """
            SELECT t.name FROM video_tags vt
            JOIN tags t ON vt.tag_id = t.id
            WHERE vt.video_id = ?
        """,
            (video_id,),
        )
        tags_rows = await tags_cursor.fetchall()
        video_data["tags"] = [tag[0] for tag in tags_rows]

        video_response = VideoResponse(**video_data)

        return DownloadStatus(
            id=video_id,
            status=video_data["status"],
            progress=video_data["progress"],
            error_message=video_data["error_message"],
            video=video_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_download_status_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{video_id}/progress")
async def stream_download_progress(
    video_id: str,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Stream download progress as Server-Sent Events."""

    async def event_generator() -> Any:
        """Generate SSE events."""
        import json as _json

        db_path = settings.DATABASE_PATH

        # Use a dedicated connection for the long-running SSE stream
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            # Check if video exists
            cursor = await db.execute(
                "SELECT id, status FROM videos WHERE id = ?", (video_id,)
            )
            row = await cursor.fetchone()
            if not row:
                yield "event: error\ndata: {\"error\": \"Video not found\"}\n\n"
                return

            # Stream progress updates until complete
            previous_progress = -1.0
            previous_status = ""
            while True:
                cursor = await db.execute(
                    "SELECT status, progress, error_message FROM videos WHERE id = ?",
                    (video_id,),
                )
                row = await cursor.fetchone()

                if not row:
                    # Video was deleted (e.g. duplicate cleanup)
                    yield f'data: {{"id": "{video_id}", "status": "duplicate", "progress": 0, "error_message": "Video is a duplicate"}}\n\n'
                    break

                status_val = row[0]
                progress = row[1] or 0
                error_message = row[2]

                # Send update if progress or status changed
                if progress != previous_progress or status_val != previous_status:
                    previous_progress = progress
                    previous_status = status_val
                    error_json = _json.dumps(error_message)
                    yield f'data: {{"id": "{video_id}", "status": "{status_val}", "progress": {progress}, "error_message": {error_json}}}\n\n'

                # Stop if completed or failed
                if status_val in ("completed", "failed", "duplicate"):
                    break

                await asyncio.sleep(1)

        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_download(
    video_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    """Cancel a pending download."""
    try:
        db.row_factory = aiosqlite.Row

        # Check if video exists
        cursor = await db.execute("SELECT status FROM videos WHERE id = ?", (video_id,))
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Download not found",
            )

        status_val = row[0]

        # Can only cancel pending or processing tasks
        if status_val not in ("pending", "processing"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel download in {status_val} state",
            )

        # Cancel the task if it exists
        if video_id in active_tasks:
            active_tasks[video_id].cancel()
            del active_tasks[video_id]

        # Update status
        await db.execute(
            "UPDATE videos SET status = ? WHERE id = ?",
            ("cancelled", video_id),
        )
        await db.commit()

        logger.info("download_cancelled", video_id=video_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("cancel_download_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
