import asyncio
from typing import Any, Callable, Optional

import structlog
import yt_dlp

logger = structlog.get_logger()


async def extract_metadata(url: str, flat: bool = False) -> dict[str, Any]:
    """Extract metadata from a video URL using yt-dlp.

    Args:
        url: Video or playlist URL.
        flat: If True, use extract_flat='in_playlist' so playlist entries
              contain basic info without fetching each video's full metadata.
              Useful for detecting playlists quickly.
    """
    loop = asyncio.get_event_loop()

    def _extract() -> dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist" if flat else False,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info

    try:
        info = await loop.run_in_executor(None, _extract)
        return info
    except Exception as e:
        logger.error("metadata_extraction_failed", url=url, error=str(e))
        raise


async def download_video(
    url: str,
    output_path: str,
    quality: int = 1080,
    format_str: str = "mp4",
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> dict[str, Any]:
    """
    Download a video using yt-dlp.

    Args:
        url: Video URL
        output_path: Directory to save the video
        quality: Preferred quality in pixels
        format_str: Output format (mp4, webm, etc.)
        progress_callback: Function to call with progress updates

    Returns:
        Dictionary with downloaded file information
    """
    loop = asyncio.get_event_loop()

    def _progress_hook(d: dict[str, Any]) -> None:
        """Hook called by yt-dlp with progress updates."""
        if progress_callback:
            progress_callback(d)

    def _download() -> dict[str, Any]:
        # Format selection: prefer mp4/webm with quality close to requested
        format_spec = (
            f"best[ext={format_str}][height<={quality}]/best[height<={quality}]/"
            f"best[ext={format_str}]/best"
        )

        ydl_opts = {
            "format": format_spec,
            "outtmpl": f"{output_path}/%(title)s.%(ext)s",
            "quiet": False,
            "no_warnings": False,
            "noplaylist": True,
            "progress_hooks": [_progress_hook],
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
            "extractor_args": {
                "youtube": {
                    "skip": ["hls"],
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            return result

    try:
        logger.info("download_started", url=url, output_path=output_path)
        result = await loop.run_in_executor(None, _download)
        logger.info(
            "download_completed",
            url=url,
            filename=result.get("filename", "unknown"),
        )
        return result
    except Exception as e:
        logger.error("download_failed", url=url, error=str(e))
        raise
