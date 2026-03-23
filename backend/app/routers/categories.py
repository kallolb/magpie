from typing import Any

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.models.category import CategoryCreate, CategoryResponse
from app.utils.file_utils import ensure_category_dir

logger = structlog.get_logger()

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> list[CategoryResponse]:
    """List all categories with video counts."""
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT c.name, c.description, c.created_at,
                   COUNT(DISTINCT v.id) as video_count
            FROM categories c
            LEFT JOIN videos v ON c.name = v.category
            GROUP BY c.name
            ORDER BY c.name
        """
        )
        rows = await cursor.fetchall()

        categories = [CategoryResponse(**dict(row)) for row in rows]
        return categories

    except Exception as e:
        logger.error("list_categories_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    request: CategoryCreate,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> CategoryResponse:
    """Create a new category."""
    try:
        db.row_factory = aiosqlite.Row

        # Insert category
        await db.execute(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            (request.name, request.description),
        )
        await db.commit()

        # Create directory
        ensure_category_dir(settings.STORAGE_ROOT, request.name)

        # Fetch and return
        cursor = await db.execute(
            "SELECT name, description, created_at FROM categories WHERE name = ?",
            (request.name,),
        )
        row = await cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create category",
            )

        logger.info("category_created", name=request.name)

        return CategoryResponse(
            name=row[0],
            description=row[1],
            created_at=row[2],
            video_count=0,
        )

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )
        logger.error("create_category_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/{category_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_name: str,
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> None:
    """Delete a category (moves videos to uncategorized)."""
    try:
        db.row_factory = aiosqlite.Row

        # Prevent deletion of 'uncategorized'
        if category_name == "uncategorized":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the 'uncategorized' category",
            )

        # Check if category exists
        cursor = await db.execute(
            "SELECT name FROM categories WHERE name = ?", (category_name,)
        )
        if not await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        # Move videos to uncategorized
        await db.execute(
            "UPDATE videos SET category = ? WHERE category = ?",
            ("uncategorized", category_name),
        )

        # Delete category
        await db.execute("DELETE FROM categories WHERE name = ?", (category_name,))
        await db.commit()

        logger.info("category_deleted", name=category_name)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_category_failed", category=category_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
