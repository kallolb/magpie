from typing import Any

import aiosqlite
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.database import get_db_dep

logger = structlog.get_logger()

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("")
async def get_analytics(
    settings: Settings = Depends(get_settings),
    db: aiosqlite.Connection = Depends(get_db_dep),
) -> dict[str, Any]:
    """Return comprehensive analytics computed from existing data."""
    db.row_factory = aiosqlite.Row

    # --- Storage Analytics ---

    # Total storage
    cursor = await db.execute(
        "SELECT COALESCE(SUM(file_size_bytes), 0) as total, COUNT(*) as count FROM videos WHERE status = 'completed'"
    )
    row = await cursor.fetchone()
    total_storage = row["total"]
    total_completed = row["count"]

    # Storage by category
    cursor = await db.execute(
        """SELECT category, COUNT(*) as count, COALESCE(SUM(file_size_bytes), 0) as total_bytes
           FROM videos WHERE status = 'completed'
           GROUP BY category ORDER BY total_bytes DESC"""
    )
    storage_by_category = [dict(r) for r in await cursor.fetchall()]

    # Storage by platform
    cursor = await db.execute(
        """SELECT platform, COUNT(*) as count, COALESCE(SUM(file_size_bytes), 0) as total_bytes
           FROM videos WHERE status = 'completed'
           GROUP BY platform ORDER BY total_bytes DESC"""
    )
    storage_by_platform = [dict(r) for r in await cursor.fetchall()]

    # Largest videos
    cursor = await db.execute(
        """SELECT id, title, file_size_bytes, duration_secs, platform, category
           FROM videos WHERE status = 'completed' AND file_size_bytes IS NOT NULL
           ORDER BY file_size_bytes DESC LIMIT 10"""
    )
    largest_videos = [dict(r) for r in await cursor.fetchall()]

    # Storage growth over time (monthly)
    cursor = await db.execute(
        """SELECT strftime('%Y-%m', created_at) as month,
                  COUNT(*) as count,
                  COALESCE(SUM(file_size_bytes), 0) as total_bytes
           FROM videos WHERE status = 'completed'
           GROUP BY month ORDER BY month"""
    )
    monthly_rows = [dict(r) for r in await cursor.fetchall()]
    # Compute cumulative
    cumulative = 0
    storage_growth = []
    for row in monthly_rows:
        cumulative += row["total_bytes"]
        storage_growth.append({
            "month": row["month"],
            "count": row["count"],
            "monthly_bytes": row["total_bytes"],
            "cumulative_bytes": cumulative,
        })

    # --- Video Collection Analytics ---

    # Videos by status
    cursor = await db.execute(
        "SELECT status, COUNT(*) as count FROM videos GROUP BY status ORDER BY count DESC"
    )
    videos_by_status = [dict(r) for r in await cursor.fetchall()]

    # Videos by platform
    cursor = await db.execute(
        "SELECT platform, COUNT(*) as count FROM videos GROUP BY platform ORDER BY count DESC"
    )
    videos_by_platform = [dict(r) for r in await cursor.fetchall()]

    # Videos by category
    cursor = await db.execute(
        "SELECT category, COUNT(*) as count FROM videos GROUP BY category ORDER BY count DESC"
    )
    videos_by_category = [dict(r) for r in await cursor.fetchall()]

    # Top uploaders
    cursor = await db.execute(
        """SELECT uploader, COUNT(*) as count, COALESCE(SUM(file_size_bytes), 0) as total_bytes
           FROM videos WHERE uploader IS NOT NULL AND uploader != ''
           GROUP BY uploader ORDER BY count DESC LIMIT 10"""
    )
    top_uploaders = [dict(r) for r in await cursor.fetchall()]

    # Download success rate
    cursor = await db.execute(
        """SELECT
             COUNT(*) as total,
             SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
             SUM(CASE WHEN status = 'duplicate' THEN 1 ELSE 0 END) as duplicate
           FROM videos"""
    )
    rate_row = await cursor.fetchone()
    download_success_rate = dict(rate_row)

    # --- Content Analytics ---

    # Duration distribution
    cursor = await db.execute(
        """SELECT
             SUM(CASE WHEN duration_secs < 60 THEN 1 ELSE 0 END) as under_1min,
             SUM(CASE WHEN duration_secs >= 60 AND duration_secs < 300 THEN 1 ELSE 0 END) as min_1_to_5,
             SUM(CASE WHEN duration_secs >= 300 AND duration_secs < 900 THEN 1 ELSE 0 END) as min_5_to_15,
             SUM(CASE WHEN duration_secs >= 900 AND duration_secs < 3600 THEN 1 ELSE 0 END) as min_15_to_60,
             SUM(CASE WHEN duration_secs >= 3600 THEN 1 ELSE 0 END) as over_1hr
           FROM videos WHERE status = 'completed' AND duration_secs IS NOT NULL"""
    )
    dur_row = await cursor.fetchone()
    duration_distribution = [
        {"label": "< 1 min", "count": dur_row["under_1min"] or 0},
        {"label": "1-5 min", "count": dur_row["min_1_to_5"] or 0},
        {"label": "5-15 min", "count": dur_row["min_5_to_15"] or 0},
        {"label": "15-60 min", "count": dur_row["min_15_to_60"] or 0},
        {"label": "1+ hr", "count": dur_row["over_1hr"] or 0},
    ]

    # Resolution breakdown
    cursor = await db.execute(
        """SELECT COALESCE(resolution, 'unknown') as resolution, COUNT(*) as count
           FROM videos WHERE status = 'completed'
           GROUP BY resolution ORDER BY count DESC"""
    )
    resolution_breakdown = [dict(r) for r in await cursor.fetchall()]

    # Size distribution
    cursor = await db.execute(
        """SELECT
             SUM(CASE WHEN file_size_bytes < 52428800 THEN 1 ELSE 0 END) as under_50mb,
             SUM(CASE WHEN file_size_bytes >= 52428800 AND file_size_bytes < 209715200 THEN 1 ELSE 0 END) as mb_50_to_200,
             SUM(CASE WHEN file_size_bytes >= 209715200 AND file_size_bytes < 1073741824 THEN 1 ELSE 0 END) as mb_200_to_1gb,
             SUM(CASE WHEN file_size_bytes >= 1073741824 THEN 1 ELSE 0 END) as over_1gb
           FROM videos WHERE status = 'completed' AND file_size_bytes IS NOT NULL"""
    )
    size_row = await cursor.fetchone()
    size_distribution = [
        {"label": "< 50 MB", "count": size_row["under_50mb"] or 0},
        {"label": "50-200 MB", "count": size_row["mb_50_to_200"] or 0},
        {"label": "200 MB - 1 GB", "count": size_row["mb_200_to_1gb"] or 0},
        {"label": "1+ GB", "count": size_row["over_1gb"] or 0},
    ]

    # Tag usage (top 15)
    cursor = await db.execute(
        """SELECT t.name, COUNT(vt.video_id) as count
           FROM tags t JOIN video_tags vt ON t.id = vt.tag_id
           GROUP BY t.id ORDER BY count DESC LIMIT 15"""
    )
    top_tags = [dict(r) for r in await cursor.fetchall()]

    # Average duration overall and per platform
    cursor = await db.execute(
        "SELECT COALESCE(AVG(duration_secs), 0) as avg_duration FROM videos WHERE status = 'completed' AND duration_secs IS NOT NULL"
    )
    avg_row = await cursor.fetchone()
    avg_duration = round(avg_row["avg_duration"])

    cursor = await db.execute(
        """SELECT platform, ROUND(AVG(duration_secs)) as avg_duration, COUNT(*) as count
           FROM videos WHERE status = 'completed' AND duration_secs IS NOT NULL
           GROUP BY platform ORDER BY count DESC"""
    )
    avg_duration_by_platform = [dict(r) for r in await cursor.fetchall()]

    # --- Activity Analytics ---

    # Downloads over time (daily, last 30 days)
    cursor = await db.execute(
        """SELECT strftime('%Y-%m-%d', created_at) as day, COUNT(*) as count
           FROM videos
           WHERE created_at >= datetime('now', '-30 days')
           GROUP BY day ORDER BY day"""
    )
    daily_downloads = [dict(r) for r in await cursor.fetchall()]

    # Downloads by day of week
    cursor = await db.execute(
        """SELECT
             CASE CAST(strftime('%w', created_at) AS INTEGER)
               WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue'
               WHEN 3 THEN 'Wed' WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri'
               WHEN 6 THEN 'Sat'
             END as day_name,
             CAST(strftime('%w', created_at) AS INTEGER) as day_num,
             COUNT(*) as count
           FROM videos GROUP BY day_num ORDER BY day_num"""
    )
    downloads_by_day = [dict(r) for r in await cursor.fetchall()]

    # Recent activity (last 7 days vs prior 7 days)
    cursor = await db.execute(
        """SELECT
             SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as last_7_days,
             SUM(CASE WHEN created_at >= datetime('now', '-14 days') AND created_at < datetime('now', '-7 days') THEN 1 ELSE 0 END) as prior_7_days
           FROM videos"""
    )
    activity_row = await cursor.fetchone()
    recent_activity = {
        "last_7_days": activity_row["last_7_days"] or 0,
        "prior_7_days": activity_row["prior_7_days"] or 0,
    }

    # Loop markers stats
    cursor = await db.execute(
        """SELECT COUNT(*) as total_loops,
                  COUNT(DISTINCT video_id) as videos_with_loops
           FROM loop_markers"""
    )
    loop_row = await cursor.fetchone()
    loop_marker_stats = dict(loop_row)

    logger.info("analytics_computed")

    return {
        "storage": {
            "total_bytes": total_storage,
            "total_completed": total_completed,
            "by_category": storage_by_category,
            "by_platform": storage_by_platform,
            "largest_videos": largest_videos,
            "growth": storage_growth,
        },
        "collection": {
            "by_status": videos_by_status,
            "by_platform": videos_by_platform,
            "by_category": videos_by_category,
            "top_uploaders": top_uploaders,
            "download_success_rate": download_success_rate,
        },
        "content": {
            "duration_distribution": duration_distribution,
            "resolution_breakdown": resolution_breakdown,
            "size_distribution": size_distribution,
            "top_tags": top_tags,
            "avg_duration": avg_duration,
            "avg_duration_by_platform": avg_duration_by_platform,
        },
        "activity": {
            "daily_downloads": daily_downloads,
            "by_day_of_week": downloads_by_day,
            "recent": recent_activity,
            "loop_markers": loop_marker_stats,
        },
    }
