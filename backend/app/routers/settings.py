from typing import Any

import aiosqlite
import structlog
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.database import get_db_dep
from app.utils.file_utils import get_storage_stats

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=dict[str, Any])
async def get_settings_endpoint(
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get current configuration (non-sensitive)."""
    return {
        "storage_root": settings.STORAGE_ROOT,
        "default_quality": settings.DEFAULT_QUALITY,
        "default_format": settings.DEFAULT_FORMAT,
        "max_concurrent_downloads": settings.MAX_CONCURRENT_DOWNLOADS,
        "api_host": settings.API_HOST,
        "api_port": settings.API_PORT,
    }


@router.get("/health", response_model=dict[str, Any])
async def health_check(
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, Any]:
    """Health check endpoint."""
    try:
        # Test database connectivity
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()

        # Get storage stats
        stats = get_storage_stats(settings.STORAGE_ROOT)

        return {
            "status": "healthy",
            "database": "connected",
            "storage": {
                "total_bytes": stats["total_bytes"],
                "used_bytes": stats["used_bytes"],
                "free_bytes": stats["free_bytes"],
                "local_used_bytes": stats["local_used_bytes"],
            },
        }

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }
