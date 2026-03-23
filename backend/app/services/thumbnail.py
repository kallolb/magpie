import asyncio
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()


async def save_thumbnail(
    url: str, storage_root: str, video_id: str
) -> Optional[str]:
    """
    Download and save a thumbnail image.

    Args:
        url: Thumbnail URL
        storage_root: Root storage directory
        video_id: Video ID for naming

    Returns:
        Relative path to saved thumbnail or None if failed
    """
    if not url:
        return None

    try:
        thumbnails_dir = Path(storage_root) / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_path = thumbnails_dir / f"{video_id}.jpg"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        thumbnail_path.write_bytes(response.content)
        logger.info("thumbnail_saved", video_id=video_id, path=str(thumbnail_path))

        return str(thumbnail_path.relative_to(storage_root))

    except Exception as e:
        logger.warning("thumbnail_download_failed", video_id=video_id, error=str(e))
        return None


async def generate_thumbnail(
    video_file: str, storage_root: str, video_id: str
) -> Optional[str]:
    """
    Generate a thumbnail from a video file using ffmpeg.

    Args:
        video_file: Absolute path to the video file
        storage_root: Root storage directory
        video_id: Video ID for naming

    Returns:
        Relative path to saved thumbnail or None if failed
    """
    try:
        thumbnails_dir = Path(storage_root) / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_path = thumbnails_dir / f"{video_id}.jpg"

        if not Path(video_file).exists():
            logger.warning("video_file_not_found", video_id=video_id, path=video_file)
            return None

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_file,
            "-ss", "00:00:01", "-vframes", "1",
            "-vf", "scale=640:-1",
            "-y", str(thumbnail_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode != 0 or not thumbnail_path.exists():
            logger.warning("thumbnail_generation_failed", video_id=video_id)
            return None

        logger.info("thumbnail_generated", video_id=video_id, path=str(thumbnail_path))
        return str(thumbnail_path.relative_to(storage_root))

    except Exception as e:
        logger.warning("thumbnail_generation_error", video_id=video_id, error=str(e))
        return None
