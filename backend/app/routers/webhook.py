import asyncio
import uuid
from typing import Any, Optional

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.routers.downloads import _background_download
from app.services.notifier import NotificationManager, get_notifier

logger = structlog.get_logger()

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# Task tracker
active_tasks: dict[str, asyncio.Task[dict[str, Any]]] = {}


@router.post("/ingest", response_model=dict[str, Any])
async def webhook_ingest(
    body: dict[str, Any],
    x_api_key: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
    notifier: NotificationManager = Depends(get_notifier),
) -> dict[str, Any]:
    """
    Universal webhook endpoint for triggering downloads.

    Expected body:
    {
        "source": "chatbot_name",
        "url": "https://...",
        "category": "optional_category",
        "tags": ["tag1", "tag2"],
        "callback_id": "optional_callback_id"
    }
    """
    try:
        # Validate API key
        if x_api_key != settings.API_KEY:
            logger.warning("webhook_unauthorized_attempt", api_key_provided=bool(x_api_key))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Validate required fields
        url = body.get("url")
        source = body.get("source", "webhook")

        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field: url",
            )

        category = body.get("category")
        tags = body.get("tags")
        callback_id = body.get("callback_id")

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
                url,
                "unknown",
                "Processing...",
                "pending",
                category or "uncategorized",
                0,
            ),
        )
        await db.commit()

        # Register callback if provided
        if callback_id:
            # For now, we'll pass the callback_id in triggered_by
            triggered_by = f"callback:{callback_id}"
        else:
            triggered_by = f"webhook:{source}"

        # Start background task
        task = asyncio.create_task(
            _background_download(
                db_path=settings.DATABASE_PATH,
                storage_root=settings.STORAGE_ROOT,
                video_id=video_id,
                url=url,
                category=category,
                tags=tags,
                quality=settings.DEFAULT_QUALITY,
                triggered_by=triggered_by,
            )
        )
        active_tasks[video_id] = task

        logger.info(
            "webhook_download_started",
            video_id=video_id,
            url=url,
            source=source,
            callback_id=callback_id,
        )

        return {
            "status": "queued",
            "video_id": video_id,
            "message": "Download queued successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("webhook_ingest_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
