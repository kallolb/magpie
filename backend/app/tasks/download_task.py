import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import structlog

from app.services.categorizer import auto_categorize
from app.services.downloader import download_video, extract_metadata
from app.services.notifier import NotificationManager
from app.services.search import rebuild_fts_tags
from app.services.thumbnail import generate_thumbnail, save_thumbnail
from app.utils.file_utils import ensure_category_dir, get_video_path, safe_filename
from app.utils.url_parser import detect_platform, extract_video_id

logger = structlog.get_logger()


async def _update_progress(db: aiosqlite.Connection, video_id: str, progress: float) -> None:
    """Update download progress in the database."""
    try:
        await db.execute(
            "UPDATE videos SET progress = ?, updated_at = datetime('now') WHERE id = ?",
            (progress, video_id),
        )
        await db.commit()
    except Exception:
        pass  # Don't let progress updates break the download


async def _apply_tags(db: aiosqlite.Connection, video_id: str, tags: list[str]) -> None:
    """Create tags and link them to a video."""
    for tag_name in tags:
        await db.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,)
        )
        await db.commit()

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
    await db.commit()


async def _download_single_video(
    db: aiosqlite.Connection,
    storage_root: str,
    video_id: str,
    url: str,
    category: Optional[str],
    tags: Optional[list[str]],
    quality: int,
    triggered_by: str,
    notifier: Optional[NotificationManager] = None,
    metadata: Optional[dict[str, Any]] = None,
    progress_offset: float = 0.0,
    progress_scale: float = 100.0,
) -> dict[str, Any]:
    """
    Download a single video and update its DB record.

    Args:
        db: Database connection
        storage_root: Root storage directory
        video_id: Video ID (uuid) for the DB record
        url: Direct video URL
        category: Optional category
        tags: Optional list of tags
        quality: Preferred quality
        triggered_by: Who triggered the download
        notifier: Optional notification manager
        metadata: Pre-fetched metadata dict (if None, will be extracted)
        progress_offset: Base progress value (for playlist items)
        progress_scale: How much of the 0-100 range this download occupies
    """
    # Extract metadata if not provided
    if metadata is None:
        logger.info("extracting_metadata", video_id=video_id)
        metadata = await extract_metadata(url)

    platform = detect_platform(url)
    platform_id = extract_video_id(url, platform)
    title = metadata.get("title", "Unknown")
    description = metadata.get("description")
    uploader = metadata.get("uploader")
    upload_date = metadata.get("upload_date")
    raw_duration = metadata.get("duration")
    duration_secs = int(raw_duration) if raw_duration is not None else None
    ext = metadata.get("ext", "mp4")

    # Check for duplicates by platform_id
    if platform_id:
        cursor = await db.execute(
            "SELECT id FROM videos WHERE platform_id = ? AND platform = ?",
            (platform_id, platform),
        )
        existing = await cursor.fetchone()
        if existing:
            logger.warning(
                "video_already_exists", platform_id=platform_id, platform=platform
            )
            await db.execute(
                "DELETE FROM videos WHERE id = ?", (video_id,)
            )
            await db.commit()
            return {"status": "duplicate", "error": f"Video already downloaded: {existing[0]}"}

    # Auto-categorize if needed
    if not category:
        category = auto_categorize(title, description, platform, duration_secs)
        logger.info("auto_categorized", video_id=video_id, category=category)
    else:
        await db.execute(
            "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
            (category, "User-created category"),
        )
        await db.commit()

    # Create output directory and determine file path
    ensure_category_dir(storage_root, category)
    safe_title = safe_filename(title)
    filename = f"{safe_title}.{ext}"
    relative_path = f"categories/{category}/{filename}"
    full_path = get_video_path(storage_root, category, filename)

    logger.info("starting_download", video_id=video_id, title=title)

    # Download video with progress tracking
    import asyncio as _asyncio
    _loop = _asyncio.get_event_loop()
    _last_progress = [0.0]

    def progress_callback(d: dict[str, Any]) -> None:
        dl_status = d.get("status", "unknown")
        if dl_status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            if total > 0:
                raw_progress = round((downloaded / total) * 100, 1)
                # Scale progress into assigned range
                scaled = progress_offset + (raw_progress / 100.0) * progress_scale
                if scaled - _last_progress[0] >= 2.0 or raw_progress >= 100:
                    _last_progress[0] = scaled
                    _loop.create_task(_update_progress(db, video_id, round(scaled, 1)))

    output_dir = str(Path(full_path).parent)
    await download_video(
        url, output_dir, quality=quality, format_str=ext, progress_callback=progress_callback
    )

    # Get file size and resolution
    video_file = Path(full_path)
    file_size_bytes = video_file.stat().st_size if video_file.exists() else 0
    resolution = metadata.get("height", 1080)

    # Save thumbnail (download from URL, or generate from video file)
    thumbnail_url = metadata.get("thumbnail")
    thumbnail_path = await save_thumbnail(thumbnail_url, storage_root, video_id)
    if not thumbnail_path:
        thumbnail_path = await generate_thumbnail(full_path, storage_root, video_id)

    # Update video record
    await db.execute(
        """
        UPDATE videos SET
            platform = ?, platform_id = ?, title = ?, description = ?,
            uploader = ?, upload_date = ?, duration_secs = ?,
            file_path = ?, file_size_bytes = ?, thumbnail_path = ?,
            category = ?, status = ?, resolution = ?,
            progress = 100, updated_at = datetime('now')
        WHERE id = ?
    """,
        (
            platform,
            platform_id,
            title,
            description,
            uploader,
            upload_date,
            duration_secs,
            relative_path,
            file_size_bytes,
            thumbnail_path,
            category,
            "completed",
            f"{resolution}p",
            video_id,
        ),
    )
    await db.commit()

    # Apply tags
    if tags:
        await _apply_tags(db, video_id, tags)

    # Update FTS index
    await rebuild_fts_tags(db, video_id)

    # Log download
    await db.execute(
        """
        INSERT INTO download_log (video_id, triggered_by, completed_at, status)
        VALUES (?, ?, datetime('now'), ?)
    """,
        (video_id, triggered_by, "success"),
    )
    await db.commit()

    logger.info("download_completed", video_id=video_id, file_path=relative_path)

    # Notify if callback provided
    if notifier and triggered_by.startswith("callback:"):
        callback_id = triggered_by.replace("callback:", "")
        video_info = {
            "id": video_id,
            "title": title,
            "url": url,
            "platform": platform,
            "category": category,
            "file_path": relative_path,
        }
        await notifier.notify_complete(video_id, video_info, callback_id)

    return {
        "status": "completed",
        "video_id": video_id,
        "file_path": relative_path,
        "file_size": file_size_bytes,
    }


async def process_download(
    db_path: str,
    storage_root: str,
    video_id: str,
    url: str,
    category: Optional[str],
    tags: Optional[list[str]],
    quality: int,
    triggered_by: str,
    notifier: Optional[NotificationManager] = None,
) -> dict[str, Any]:
    """
    Main download pipeline.  Handles both single videos and playlists.

    Args:
        db_path: Path to database
        storage_root: Root storage directory
        video_id: Video ID for the original DB record
        url: Video or playlist URL
        category: Optional category
        tags: Optional list of tags
        quality: Preferred quality
        triggered_by: Who triggered the download
        notifier: Optional notification manager

    Returns:
        Download result dict
    """
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        try:
            logger.info("download_pipeline_started", video_id=video_id, url=url)

            # Update status to 'processing'
            await db.execute(
                "UPDATE videos SET status = ?, progress = ? WHERE id = ?",
                ("processing", 0, video_id),
            )
            await db.commit()

            # Step 1: Extract metadata (flat mode to quickly detect playlists)
            logger.info("extracting_metadata", video_id=video_id)
            metadata = await extract_metadata(url, flat=True)

            # Step 2: Check if this is a playlist
            is_playlist = (
                metadata.get("_type") == "playlist"
                and "entries" in metadata
            )

            if is_playlist:
                return await _process_playlist(
                    db=db,
                    storage_root=storage_root,
                    original_video_id=video_id,
                    url=url,
                    metadata=metadata,
                    category=category,
                    tags=tags,
                    quality=quality,
                    triggered_by=triggered_by,
                    notifier=notifier,
                )
            else:
                # Single video -- re-extract full metadata (flat mode may lack details)
                full_metadata = await extract_metadata(url)
                return await _download_single_video(
                    db=db,
                    storage_root=storage_root,
                    video_id=video_id,
                    url=url,
                    category=category,
                    tags=tags,
                    quality=quality,
                    triggered_by=triggered_by,
                    notifier=notifier,
                    metadata=full_metadata,
                )

        except Exception as e:
            error_msg = str(e)
            logger.error("download_failed", video_id=video_id, error=error_msg)

            # Update status to error
            await db.execute(
                "UPDATE videos SET status = ?, error_message = ?, updated_at = datetime('now') WHERE id = ?",
                ("failed", error_msg, video_id),
            )

            # Log the failure
            await db.execute(
                """
                INSERT INTO download_log (video_id, triggered_by, completed_at, status)
                VALUES (?, ?, datetime('now'), ?)
            """,
                (video_id, triggered_by, "failed"),
            )
            await db.commit()

            # Notify of error if callback provided
            if notifier and triggered_by.startswith("callback:"):
                callback_id = triggered_by.replace("callback:", "")
                await notifier.notify_error(video_id, error_msg, callback_id)

            return {"status": "failed", "video_id": video_id, "error": error_msg}


async def _process_playlist(
    db: aiosqlite.Connection,
    storage_root: str,
    original_video_id: str,
    url: str,
    metadata: dict[str, Any],
    category: Optional[str],
    tags: Optional[list[str]],
    quality: int,
    triggered_by: str,
    notifier: Optional[NotificationManager] = None,
) -> dict[str, Any]:
    """
    Handle a playlist URL by creating a separate DB record for each video.

    The original DB record is marked as completed with a descriptive title.
    Each playlist entry gets its own uuid, DB record, download, thumbnail, etc.
    """
    entries = list(metadata.get("entries", []))
    # Filter out None entries (private/deleted videos)
    entries = [e for e in entries if e is not None]
    playlist_title = metadata.get("title", "Unknown Playlist")
    total_videos = len(entries)

    logger.info(
        "playlist_detected",
        video_id=original_video_id,
        playlist_title=playlist_title,
        total_videos=total_videos,
    )

    # Mark the original record as a completed playlist placeholder
    await db.execute(
        """
        UPDATE videos SET
            title = ?,
            status = ?,
            progress = 100,
            platform = ?,
            description = ?,
            updated_at = datetime('now')
        WHERE id = ?
    """,
        (
            f"Playlist: {playlist_title} ({total_videos} videos)",
            "completed",
            detect_platform(url),
            f"Playlist containing {total_videos} videos. Individual videos have separate records.",
            original_video_id,
        ),
    )
    await db.commit()

    if total_videos == 0:
        logger.warning("playlist_empty", video_id=original_video_id)
        return {
            "status": "completed",
            "video_id": original_video_id,
            "playlist": True,
            "total_videos": 0,
        }

    progress_per_video = 100.0 / total_videos
    results = []
    succeeded = 0
    failed = 0

    for idx, entry in enumerate(entries):
        entry_video_id = str(uuid.uuid4())
        entry_url = entry.get("url") or entry.get("webpage_url", "")

        # For YouTube flat-extracted entries, the url may be just the video id
        if entry_url and not entry_url.startswith("http"):
            entry_url = f"https://www.youtube.com/watch?v={entry_url}"

        entry_title = entry.get("title", f"Video {idx + 1}")

        logger.info(
            "playlist_video_start",
            playlist_video_id=entry_video_id,
            index=idx + 1,
            total=total_videos,
            title=entry_title,
        )

        # Insert a new DB record for this playlist entry
        await db.execute(
            """
            INSERT INTO videos (id, source_url, platform, title, status, progress, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
            (
                entry_video_id,
                entry_url,
                detect_platform(entry_url),
                entry_title,
                "processing",
                0,
                category or "uncategorized",
            ),
        )
        await db.commit()

        try:
            # Extract full metadata for this individual video
            entry_metadata = await extract_metadata(entry_url)

            progress_offset = idx * progress_per_video
            result = await _download_single_video(
                db=db,
                storage_root=storage_root,
                video_id=entry_video_id,
                url=entry_url,
                category=category,
                tags=tags,
                quality=quality,
                triggered_by=triggered_by,
                notifier=None,  # Don't notify per-video; notify at end
                metadata=entry_metadata,
                progress_offset=progress_offset,
                progress_scale=progress_per_video,
            )
            results.append(result)

            if result.get("status") in ("completed", "duplicate"):
                succeeded += 1
            else:
                failed += 1

        except Exception as e:
            failed += 1
            error_msg = str(e)
            logger.error(
                "playlist_video_failed",
                video_id=entry_video_id,
                index=idx + 1,
                error=error_msg,
            )
            await db.execute(
                "UPDATE videos SET status = ?, error_message = ?, updated_at = datetime('now') WHERE id = ?",
                ("failed", error_msg, entry_video_id),
            )
            await db.execute(
                """
                INSERT INTO download_log (video_id, triggered_by, completed_at, status)
                VALUES (?, ?, datetime('now'), ?)
            """,
                (entry_video_id, triggered_by, "failed"),
            )
            await db.commit()
            results.append({"status": "failed", "video_id": entry_video_id, "error": error_msg})

    logger.info(
        "playlist_completed",
        video_id=original_video_id,
        total=total_videos,
        succeeded=succeeded,
        failed=failed,
    )

    # Notify once for the whole playlist if callback provided
    if notifier and triggered_by.startswith("callback:"):
        callback_id = triggered_by.replace("callback:", "")
        video_info = {
            "id": original_video_id,
            "title": f"Playlist: {playlist_title} ({total_videos} videos)",
            "url": url,
            "platform": detect_platform(url),
            "category": category or "uncategorized",
            "playlist": True,
            "succeeded": succeeded,
            "failed": failed,
        }
        await notifier.notify_complete(original_video_id, video_info, callback_id)

    return {
        "status": "completed",
        "video_id": original_video_id,
        "playlist": True,
        "total_videos": total_videos,
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
