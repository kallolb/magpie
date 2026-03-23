#!/usr/bin/env python3
"""Scan the storage directory for video files not tracked in the database and import them."""

import argparse
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv"}


def get_db_connection(storage_root: str) -> sqlite3.Connection:
    db_path = os.path.join(storage_root, "db", "videos.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def find_video_files(storage_root: str) -> list[tuple[str, str]]:
    """Walk categories/*/ and return list of (relative_path, category) for video files."""
    categories_dir = os.path.join(storage_root, "categories")
    if not os.path.isdir(categories_dir):
        print(f"No categories directory found at {categories_dir}")
        return []

    results = []
    for category_name in sorted(os.listdir(categories_dir)):
        category_path = os.path.join(categories_dir, category_name)
        if not os.path.isdir(category_path):
            continue
        for filename in sorted(os.listdir(category_path)):
            ext = os.path.splitext(filename)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                rel_path = f"categories/{category_name}/{filename}"
                results.append((rel_path, category_name))
    return results


def get_tracked_paths(conn: sqlite3.Connection) -> set[str]:
    """Return set of file_path values already in the database."""
    cursor = conn.execute("SELECT file_path FROM videos WHERE file_path IS NOT NULL")
    return {row["file_path"] for row in cursor.fetchall()}


def cleanup_failed_records(conn: sqlite3.Connection, storage_root: str) -> int:
    """Delete failed records with file_size_bytes=0 whose files don't exist on disk."""
    cursor = conn.execute(
        "SELECT id, file_path FROM videos WHERE status = 'failed' AND file_size_bytes = 0"
    )
    rows = cursor.fetchall()
    deleted = 0
    for row in rows:
        file_path = row["file_path"]
        if file_path:
            full_path = os.path.join(storage_root, file_path)
            if os.path.exists(full_path):
                continue
        conn.execute("DELETE FROM videos WHERE id = ?", (row["id"],))
        deleted += 1
    return deleted


def import_files(
    conn: sqlite3.Connection, storage_root: str, files: list[tuple[str, str]], tracked: set[str]
) -> int:
    """Import untracked video files into the database. Returns count of imported files."""
    imported = 0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    for rel_path, category in files:
        if rel_path in tracked:
            continue

        full_path = os.path.join(storage_root, rel_path)
        filename = os.path.basename(rel_path)
        title = os.path.splitext(filename)[0]
        file_size = os.stat(full_path).st_size

        video_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO videos
               (id, source_url, platform, title, file_path, file_size_bytes,
                category, status, progress, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                video_id,
                "imported://local",
                "unknown",
                title,
                rel_path,
                file_size,
                category,
                "completed",
                100,
                now,
                now,
            ),
        )
        print(f"  Imported: {rel_path} ({file_size} bytes)")
        imported += 1

    return imported


def main():
    parser = argparse.ArgumentParser(description="Import existing video files into the database.")
    parser.add_argument(
        "storage_root",
        nargs="?",
        default="./storage",
        help="Path to the storage root directory (default: ./storage)",
    )
    args = parser.parse_args()

    storage_root = os.path.abspath(args.storage_root)
    print(f"Storage root: {storage_root}")

    conn = get_db_connection(storage_root)
    try:
        # Step 1: Clean up failed records with no file on disk
        deleted = cleanup_failed_records(conn, storage_root)
        if deleted:
            print(f"Cleaned up {deleted} failed record(s) with no file on disk.")

        # Step 2: Find video files and import untracked ones
        files = find_video_files(storage_root)
        print(f"Found {len(files)} video file(s) on disk.")

        tracked = get_tracked_paths(conn)
        print(f"Already tracked in DB: {len(tracked)} file(s).")

        imported = import_files(conn, storage_root, files, tracked)

        conn.commit()

        # Summary
        print()
        print("=== Summary ===")
        print(f"  Video files on disk: {len(files)}")
        print(f"  Already tracked:     {len(files) - imported}")
        print(f"  Newly imported:      {imported}")
        print(f"  Failed records cleaned: {deleted}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
