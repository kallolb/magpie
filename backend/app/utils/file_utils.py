import re
import shutil
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


def safe_filename(title: str) -> str:
    """Sanitize a title for use as a filesystem filename."""
    # Remove invalid characters for filesystems
    sanitized = re.sub(r'[<>:"/\\|?*]', "", title)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)
    # Limit length to 200 chars (leaving room for extension)
    sanitized = sanitized[:200]
    return sanitized


def get_video_path(storage_root: str, category: str, filename: str) -> str:
    """Build the full path for a video file."""
    storage = Path(storage_root)
    video_path = storage / "categories" / category / filename
    return str(video_path)


def ensure_category_dir(storage_root: str, category: str) -> str:
    """Create category directory if it doesn't exist, return the path."""
    storage = Path(storage_root)
    category_dir = storage / "categories" / category
    category_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("category_dir_created", path=str(category_dir))
    return str(category_dir)


def get_storage_stats(storage_root: str) -> dict[str, Any]:
    """Get storage statistics."""
    storage = Path(storage_root)

    # Calculate used space
    total_size = 0
    for file_path in storage.rglob("*"):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    # Get filesystem stats
    try:
        stats = shutil.disk_usage(storage_root)
        return {
            "total_bytes": stats.total,
            "used_bytes": stats.used,
            "free_bytes": stats.free,
            "local_used_bytes": total_size,
        }
    except Exception as e:
        logger.warning("storage_stats_error", error=str(e))
        return {
            "total_bytes": 0,
            "used_bytes": 0,
            "free_bytes": 0,
            "local_used_bytes": total_size,
        }
