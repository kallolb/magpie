from typing import Any, Optional

import aiosqlite
import structlog

logger = structlog.get_logger()


async def search_videos(
    db: aiosqlite.Connection,
    query: str,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """
    Search for videos using FTS5 with optional category and tag filters.

    Args:
        db: Database connection
        query: FTS5 search query
        category: Optional category filter
        tags: Optional list of tag filters (OR logic)
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Tuple of (videos, total_count)
    """
    # Build FTS5 query
    fts_query = query

    # Start with FTS5 search
    sql = """
        SELECT DISTINCT v.id, v.source_url, v.platform, v.platform_id,
               v.title, v.description, v.uploader, v.upload_date,
               v.duration_secs, v.resolution, v.file_path, v.file_size_bytes,
               v.thumbnail_path, v.category, v.status, v.error_message,
               v.progress, v.created_at, v.updated_at,
               GROUP_CONCAT(t.name) as tags
        FROM videos v
        LEFT JOIN video_tags vt ON v.id = vt.video_id
        LEFT JOIN tags t ON vt.tag_id = t.id
        WHERE v.rowid IN (
            SELECT rowid FROM videos_fts WHERE videos_fts MATCH ?
        )
    """

    params: list[Any] = [fts_query]

    # Add category filter if provided
    if category:
        sql += " AND v.category = ?"
        params.append(category)

    # Add tag filters if provided (OR logic)
    if tags:
        placeholders = ",".join("?" * len(tags))
        sql += f"""
            AND v.id IN (
                SELECT DISTINCT vt.video_id FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE t.name IN ({placeholders})
            )
        """
        params.extend(tags)

    # Count query
    count_sql = f"""
        SELECT COUNT(DISTINCT v.id) as count
        FROM videos v
        LEFT JOIN video_tags vt ON v.id = vt.video_id
        LEFT JOIN tags t ON vt.tag_id = t.id
        WHERE v.rowid IN (
            SELECT rowid FROM videos_fts WHERE videos_fts MATCH ?
        )
    """

    count_params: list[Any] = [fts_query]

    if category:
        count_sql += " AND v.category = ?"
        count_params.append(category)

    if tags:
        placeholders = ",".join("?" * len(tags))
        count_sql += f"""
            AND v.id IN (
                SELECT DISTINCT vt.video_id FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE t.name IN ({placeholders})
            )
        """
        count_params.extend(tags)

    # Get total count
    count_result = await db.execute(count_sql, count_params)
    count_row = await count_result.fetchone()
    total = count_row[0] if count_row else 0

    # Add pagination and sorting
    offset = (page - 1) * per_page
    sql += " GROUP BY v.id ORDER BY v.created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    # Execute search
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()

    # Convert rows to dicts
    videos = []
    for row in rows:
        video_dict = dict(row)
        # Parse tags string back to list
        tags_str = video_dict.pop("tags", "")
        video_dict["tags"] = tags_str.split(",") if tags_str else []
        videos.append(video_dict)

    logger.info(
        "search_executed", query=query, results=len(videos), total=total, page=page
    )

    return videos, total


async def rebuild_fts_tags(db: aiosqlite.Connection, video_id: str) -> None:
    """Rebuild the FTS index entry for a video after tag changes."""
    try:
        # Get video data for FTS columns
        cursor = await db.execute(
            "SELECT rowid, title, description, uploader FROM videos WHERE id = ?",
            (video_id,),
        )
        video_row = await cursor.fetchone()
        if not video_row:
            return

        rowid = video_row[0]
        title = video_row[1] or ""
        description = video_row[2] or ""
        uploader = video_row[3] or ""

        # Get all tags for this video
        tags_cursor = await db.execute(
            """
            SELECT GROUP_CONCAT(t.name) FROM video_tags vt
            JOIN tags t ON vt.tag_id = t.id
            WHERE vt.video_id = ?
        """,
            (video_id,),
        )
        tags_row = await tags_cursor.fetchone()
        tags_str = tags_row[0].replace(",", " ") if tags_row and tags_row[0] else ""

        # Delete old FTS entry and insert updated one (standalone FTS table)
        await db.execute(
            "DELETE FROM videos_fts WHERE rowid = ?",
            (rowid,),
        )
        await db.execute(
            "INSERT INTO videos_fts(rowid, title, description, uploader, tags) VALUES(?, ?, ?, ?, ?)",
            (rowid, title, description, uploader, tags_str),
        )
    except Exception as e:
        logger.warning("fts_rebuild_failed", video_id=video_id, error=str(e))
