from typing import Any

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.models.tag import TagCreate, TagResponse

logger = structlog.get_logger()

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> list[TagResponse]:
    """List all tags with video counts."""
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT t.id, t.name,
                   COUNT(DISTINCT vt.video_id) as video_count
            FROM tags t
            LEFT JOIN video_tags vt ON t.id = vt.tag_id
            GROUP BY t.id, t.name
            ORDER BY t.name
        """
        )
        rows = await cursor.fetchall()

        tags = [TagResponse(**dict(row)) for row in rows]
        return tags

    except Exception as e:
        logger.error("list_tags_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: TagCreate,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> TagResponse:
    """Create a new tag."""
    try:
        db.row_factory = aiosqlite.Row

        # Insert tag
        await db.execute("INSERT INTO tags (name) VALUES (?)", (request.name,))
        await db.commit()

        # Fetch and return
        cursor = await db.execute("SELECT id, name FROM tags WHERE name = ?", (request.name,))
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tag",
            )

        logger.info("tag_created", name=request.name)

        return TagResponse(
            id=row[0],
            name=row[1],
            video_count=0,
        )

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag already exists",
            )
        logger.error("create_tag_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    """Delete a tag."""
    try:
        db.row_factory = aiosqlite.Row

        # Check if tag exists
        cursor = await db.execute("SELECT id FROM tags WHERE id = ?", (tag_id,))
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found",
            )

        # Delete tag (cascade will handle video_tags)
        await db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        await db.commit()

        logger.info("tag_deleted", tag_id=tag_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_tag_failed", tag_id=tag_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
