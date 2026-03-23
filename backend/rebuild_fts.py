"""One-time script to rebuild the FTS5 index for all videos."""
import asyncio
import aiosqlite


async def rebuild():
    db_path = "/data/db/videos.db"
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Drop the broken content-synced FTS table and recreate as standalone
        await db.execute("DROP TABLE IF EXISTS videos_fts")
        await db.execute(
            "CREATE VIRTUAL TABLE videos_fts USING fts5(title, description, uploader, tags)"
        )

        # Get all videos with their rowids
        cursor = await db.execute(
            "SELECT rowid, id, title, description, uploader FROM videos"
        )
        rows = await cursor.fetchall()

        for row in rows:
            rowid = row[0]
            video_id = row[1]
            title = row[2] or ""
            description = row[3] or ""
            uploader = row[4] or ""

            # Get tags
            tags_cursor = await db.execute(
                """
                SELECT GROUP_CONCAT(t.name) FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE vt.video_id = ?
                """,
                (video_id,),
            )
            tags_row = await tags_cursor.fetchone()
            tags_str = tags_row[0] if tags_row and tags_row[0] else ""

            await db.execute(
                "INSERT INTO videos_fts(rowid, title, description, uploader, tags) VALUES(?, ?, ?, ?, ?)",
                (rowid, title, description, uploader, tags_str),
            )
            print(f"Indexed: {title} [tags: {tags_str}]")

        await db.commit()
        print(f"\nRebuilt FTS index for {len(rows)} videos")


asyncio.run(rebuild())
