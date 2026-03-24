from pathlib import Path
from typing import Any, Optional

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.models.video import (
    SearchRequest,
    VideoListResponse,
    VideoResponse,
    VideoUpdate,
)
from app.services.search import rebuild_fts_tags, search_videos
from app.services.thumbnail import generate_thumbnail

logger = structlog.get_logger()

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
async def list_videos(
    category: Optional[str] = None,
    platform: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> VideoListResponse:
    """List videos with pagination and optional filtering."""
    try:
        db.row_factory = aiosqlite.Row
        per_page = min(per_page, 100)  # Cap at 100
        offset = (page - 1) * per_page

        # Build query
        sql = """
            SELECT id, source_url, platform, platform_id, title, description,
                   uploader, upload_date, duration_secs, resolution, file_path,
                   file_size_bytes, thumbnail_path, category, status,
                   error_message, progress, created_at, updated_at
            FROM videos
            WHERE 1=1
        """
        params: list[Any] = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        if platform:
            sql += " AND platform = ?"
            params.append(platform)

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        # Get total count
        count_sql = "SELECT COUNT(*) as count FROM videos WHERE 1=1"
        count_params: list[Any] = []

        if category:
            count_sql += " AND category = ?"
            count_params.append(category)

        if platform:
            count_sql += " AND platform = ?"
            count_params.append(platform)

        count_cursor = await db.execute(count_sql, count_params)
        count_row = await count_cursor.fetchone()
        total = count_row[0] if count_row else 0

        # Get paginated results
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()

        videos = []
        for row in rows:
            video_data = dict(row)

            # Get tags for this video
            tags_cursor = await db.execute(
                """
                SELECT t.name FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE vt.video_id = ?
            """,
                (video_data["id"],),
            )
            tags_rows = await tags_cursor.fetchall()
            video_data["tags"] = [tag[0] for tag in tags_rows]

            videos.append(VideoResponse(**video_data))

        return VideoListResponse(
            items=videos,
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error("list_videos_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> VideoResponse:
    """Get a single video by ID."""
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
                detail="Video not found",
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

        return VideoResponse(**video_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_video_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: str,
    update: VideoUpdate,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> VideoResponse:
    """Update a video."""
    try:
        db.row_factory = aiosqlite.Row

        # Check if video exists
        cursor = await db.execute("SELECT id FROM videos WHERE id = ?", (video_id,))
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        # Update title if provided
        if update.title is not None:
            await db.execute(
                "UPDATE videos SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (update.title, video_id),
            )

        # Update category if provided
        if update.category is not None:
            await db.execute(
                "UPDATE videos SET category = ?, updated_at = datetime('now') WHERE id = ?",
                (update.category, video_id),
            )

        # Update tags if provided
        logger.info("update_video_payload", video_id=video_id, title=update.title, category=update.category, tags=update.tags)
        if update.tags is not None:
            # Clear existing tags
            await db.execute(
                "DELETE FROM video_tags WHERE video_id = ?", (video_id,)
            )

            # Add new tags
            for tag_name in update.tags:
                await db.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,)
                )
                cursor = await db.execute(
                    "SELECT id FROM tags WHERE name = ?", (tag_name,)
                )
                tag_row = await cursor.fetchone()
                if tag_row:
                    tag_id = tag_row[0]
                    await db.execute(
                        "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
                        (video_id, tag_id),
                    )

            # Update FTS
            await rebuild_fts_tags(db, video_id)

        await db.commit()

        # Fetch and return updated video
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

        logger.info("video_updated", video_id=video_id)
        return VideoResponse(**video_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_video_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{video_id}/deletion-check")
async def check_deletion(
    video_id: str,
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict:
    """Check if a video is referenced by compilations before deletion."""
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        """SELECT DISTINCT c.id, c.title FROM compilation_clips cc
           JOIN compilations c ON cc.compilation_id = c.id
           WHERE cc.source_video_id = ?""",
        (video_id,),
    )
    rows = await cursor.fetchall()
    compilations = [{"id": r["id"], "title": r["title"]} for r in rows]
    return {
        "referenced": len(compilations) > 0,
        "compilation_count": len(compilations),
        "compilations": compilations,
    }


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    """Delete a video and its file."""
    try:
        db.row_factory = aiosqlite.Row

        # Get video info
        cursor = await db.execute(
            "SELECT file_path, thumbnail_path FROM videos WHERE id = ?",
            (video_id,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        # Delete files
        if row[0]:
            file_path = Path(settings.STORAGE_ROOT) / row[0]
            if file_path.exists():
                file_path.unlink()
                logger.info("video_file_deleted", path=str(file_path))

        if row[1]:
            thumb_path = Path(settings.STORAGE_ROOT) / row[1]
            if thumb_path.exists():
                thumb_path.unlink()
                logger.info("thumbnail_deleted", path=str(thumb_path))

        # Delete from database
        await db.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        await db.commit()

        logger.info("video_deleted", video_id=video_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_video_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/search", response_model=VideoListResponse)
async def search(
    request: SearchRequest,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> VideoListResponse:
    """Search videos using full-text search."""
    try:
        db.row_factory = aiosqlite.Row

        videos_data, total = await search_videos(
            db=db,
            query=request.query,
            category=request.category,
            tags=request.tags,
            page=request.page,
            per_page=request.per_page,
        )

        videos = [VideoResponse(**video) for video in videos_data]

        return VideoListResponse(
            items=videos,
            total=total,
            page=request.page,
            per_page=request.per_page,
        )

    except Exception as e:
        logger.error("search_failed", query=request.query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{video_id}/stream", response_model=None)
async def stream_video(
    video_id: str,
    range_header: Optional[str] = None,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> StreamingResponse | FileResponse:
    """Stream a video file with HTTP Range request support."""
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT file_path FROM videos WHERE id = ?", (video_id,)
        )
        row = await cursor.fetchone()

        if not row or not row[0]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found",
            )

        file_path = Path(settings.STORAGE_ROOT) / row[0]

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video file not found",
            )

        # Return file with appropriate headers for streaming
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=file_path.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stream_video_failed", video_id=video_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/regenerate-thumbnails")
async def regenerate_thumbnails(
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, Any]:
    """Generate thumbnails for all videos that are missing them."""
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, file_path FROM videos WHERE thumbnail_path IS NULL AND file_path IS NOT NULL AND status = 'completed'"
        )
        rows = await cursor.fetchall()

        generated = 0
        for row in rows:
            video_id = row[0]
            file_path = Path(settings.STORAGE_ROOT) / row[1]
            thumb_path = await generate_thumbnail(
                str(file_path), settings.STORAGE_ROOT, video_id
            )
            if thumb_path:
                await db.execute(
                    "UPDATE videos SET thumbnail_path = ? WHERE id = ?",
                    (thumb_path, video_id),
                )
                generated += 1

        await db.commit()
        logger.info("thumbnails_regenerated", count=generated)
        return {"generated": generated, "total": len(rows)}

    except Exception as e:
        logger.error("regenerate_thumbnails_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
