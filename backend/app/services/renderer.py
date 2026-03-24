import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import structlog

logger = structlog.get_logger()


async def probe_video(file_path: str) -> Optional[dict[str, Any]]:
    """Run ffprobe on a video file and return stream info."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        return json.loads(stdout)
    except Exception as e:
        logger.warning("ffprobe_failed", file_path=file_path, error=str(e))
        return None


def _extract_stream_info(probe_data: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant codec/resolution info from ffprobe output."""
    video_stream = None
    audio_stream = None
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "video" and not video_stream:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and not audio_stream:
            audio_stream = stream

    return {
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "width": video_stream.get("width") if video_stream else None,
        "height": video_stream.get("height") if video_stream else None,
        "resolution": f"{video_stream['width']}x{video_stream['height']}" if video_stream and video_stream.get("width") else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
    }


async def analyze_clips(
    clips: list[dict[str, Any]], storage_root: str
) -> dict[str, Any]:
    """Analyze clips for codec compatibility and return recommendation."""
    clip_infos = []
    for clip in clips:
        file_path = str(Path(storage_root) / clip["file_path"]) if clip.get("file_path") else None
        if not file_path or not Path(file_path).exists():
            clip_infos.append({
                "clip_id": clip["clip_id"],
                "source_video_id": clip["source_video_id"],
                "error": "Source file not found",
                "compatible": False,
            })
            continue

        probe = await probe_video(file_path)
        if not probe:
            clip_infos.append({
                "clip_id": clip["clip_id"],
                "source_video_id": clip["source_video_id"],
                "error": "Could not probe file",
                "compatible": False,
            })
            continue

        info = _extract_stream_info(probe)
        clip_infos.append({
            "clip_id": clip["clip_id"],
            "source_video_id": clip["source_video_id"],
            **info,
            "compatible": True,
        })

    # Determine compatibility
    valid_infos = [c for c in clip_infos if c.get("compatible") and c.get("video_codec")]
    if not valid_infos:
        return {
            "compatible": False,
            "recommendation": "reencode",
            "reason": "No valid video streams found",
            "clips": clip_infos,
            "options": [_reencode_option(True)],
        }

    codecs = {c["video_codec"] for c in valid_infos}
    resolutions = {c["resolution"] for c in valid_infos if c.get("resolution")}
    audio_codecs = {c["audio_codec"] for c in valid_infos if c.get("audio_codec")}

    compatible = len(codecs) == 1 and len(resolutions) <= 1 and len(audio_codecs) <= 1

    if compatible:
        reason = f"All clips use {codecs.pop()}"
        if resolutions:
            reason += f" at {resolutions.pop()}"
        recommendation = "copy"
    else:
        parts = []
        if len(codecs) > 1:
            parts.append(f"different codecs: {', '.join(sorted(codecs))}")
        if len(resolutions) > 1:
            parts.append(f"different resolutions: {', '.join(sorted(resolutions))}")
        if len(audio_codecs) > 1:
            parts.append(f"different audio codecs: {', '.join(sorted(audio_codecs))}")
        reason = "Clips have " + "; ".join(parts)
        recommendation = "reencode"

    # Estimate duration for time estimate
    total_duration = sum(c.get("duration", 0) for c in clips)

    options = []
    options.append({
        "mode": "copy",
        "label": "Fast (stream copy)",
        "description": "Near-instant, preserves original quality" + (
            "" if compatible else ". May have glitches due to codec/resolution mismatch"
        ),
        "estimated_time": "< 5 seconds",
        "recommended": compatible,
    })
    options.append({
        "mode": "reencode",
        "label": "Best quality (re-encode)",
        "description": "Normalizes all clips to H.264/AAC. Smooth playback guaranteed",
        "estimated_time": f"~{max(1, int(total_duration / 30))} minutes" if total_duration > 0 else "varies",
        "recommended": not compatible,
    })

    return {
        "compatible": compatible,
        "recommendation": recommendation,
        "reason": reason,
        "clips": clip_infos,
        "options": options,
    }


def _reencode_option(recommended: bool) -> dict[str, Any]:
    return {
        "mode": "reencode",
        "label": "Best quality (re-encode)",
        "description": "Re-encodes all clips to H.264/AAC",
        "estimated_time": "varies",
        "recommended": recommended,
    }


async def render_compilation(
    db_path: str,
    storage_root: str,
    compilation_id: str,
    mode: str,
) -> None:
    """Background task to render a compilation using ffmpeg."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row

        try:
            # Update status
            await db.execute(
                "UPDATE compilations SET status = 'rendering', render_mode = ?, error_message = NULL, updated_at = datetime('now') WHERE id = ?",
                (mode, compilation_id),
            )
            await db.commit()

            # Fetch clips with source file paths
            cursor = await db.execute(
                """SELECT cc.id, cc.source_video_id, cc.position, cc.start_secs, cc.end_secs,
                          v.file_path
                   FROM compilation_clips cc
                   JOIN videos v ON cc.source_video_id = v.id
                   WHERE cc.compilation_id = ?
                   ORDER BY cc.position""",
                (compilation_id,),
            )
            clips = [dict(r) for r in await cursor.fetchall()]

            if not clips:
                raise ValueError("No clips to render")

            # Check all source files exist
            for clip in clips:
                src = Path(storage_root) / clip["file_path"]
                if not src.exists():
                    raise FileNotFoundError(f"Source file missing: {clip['file_path']}")

            # Prepare temp directory
            tmp_dir = Path(storage_root) / "compilations_tmp" / compilation_id
            tmp_dir.mkdir(parents=True, exist_ok=True)

            output_dir = Path(storage_root) / "compilations"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{compilation_id}.mp4"

            total_clips = len(clips)

            if mode == "copy":
                await _render_stream_copy(db, compilation_id, clips, storage_root, tmp_dir, output_path, total_clips)
            else:
                await _render_reencode(db, compilation_id, clips, storage_root, tmp_dir, output_path, total_clips)

            # Generate thumbnail
            thumb_path = await _generate_compilation_thumbnail(str(output_path), storage_root, compilation_id)

            # Get output file size and duration
            output_size = output_path.stat().st_size if output_path.exists() else 0
            duration = await _get_duration(str(output_path))

            # Update compilation
            rel_output = str(output_path.relative_to(storage_root))
            rel_thumb = thumb_path if thumb_path else None
            await db.execute(
                """UPDATE compilations SET
                     status = 'completed', output_path = ?, output_size_bytes = ?,
                     duration_secs = ?, thumbnail_path = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (rel_output, output_size, duration, rel_thumb, compilation_id),
            )
            await db.commit()
            logger.info("compilation_rendered", compilation_id=compilation_id, mode=mode, size=output_size)

        except Exception as e:
            logger.error("compilation_render_failed", compilation_id=compilation_id, error=str(e))
            await db.execute(
                "UPDATE compilations SET status = 'failed', error_message = ?, updated_at = datetime('now') WHERE id = ?",
                (str(e), compilation_id),
            )
            await db.commit()

        finally:
            # Clean up temp directory
            tmp_dir = Path(storage_root) / "compilations_tmp" / compilation_id
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)


async def _render_stream_copy(
    db: aiosqlite.Connection, compilation_id: str,
    clips: list[dict], storage_root: str, tmp_dir: Path, output_path: Path,
    total_clips: int,
) -> None:
    """Render using stream copy (fast, no re-encoding)."""
    clip_files = []
    for i, clip in enumerate(clips):
        src = str(Path(storage_root) / clip["file_path"])
        clip_file = tmp_dir / f"clip_{i:03d}.mp4"

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", src,
            "-ss", str(clip["start_secs"]), "-to", str(clip["end_secs"]),
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            str(clip_file),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to cut clip {i + 1}")

        clip_files.append(clip_file)

        # Update progress
        progress = ((i + 1) / total_clips) * 90  # 90% for cutting, 10% for concat
        await _update_progress(db, compilation_id, progress)

    # Concatenate
    concat_file = tmp_dir / "concat.txt"
    concat_file.write_text("\n".join(f"file '{f}'" for f in clip_files))

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("Failed to concatenate clips")

    await _update_progress(db, compilation_id, 100)


async def _render_reencode(
    db: aiosqlite.Connection, compilation_id: str,
    clips: list[dict], storage_root: str, tmp_dir: Path, output_path: Path,
    total_clips: int,
) -> None:
    """Render by re-encoding all clips to uniform H.264/AAC."""
    clip_files = []
    for i, clip in enumerate(clips):
        src = str(Path(storage_root) / clip["file_path"])
        clip_file = tmp_dir / f"clip_{i:03d}.mp4"

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", src,
            "-ss", str(clip["start_secs"]), "-to", str(clip["end_secs"]),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-r", "30",
            str(clip_file),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to re-encode clip {i + 1}")

        clip_files.append(clip_file)

        progress = ((i + 1) / total_clips) * 90
        await _update_progress(db, compilation_id, progress)

    # Concatenate re-encoded clips (stream copy since they're now uniform)
    concat_file = tmp_dir / "concat.txt"
    concat_file.write_text("\n".join(f"file '{f}'" for f in clip_files))

    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("Failed to concatenate re-encoded clips")

    await _update_progress(db, compilation_id, 100)


async def _update_progress(db: aiosqlite.Connection, compilation_id: str, progress: float) -> None:
    """Update render progress in the database."""
    await db.execute(
        "UPDATE compilations SET updated_at = datetime('now') WHERE id = ?",
        (compilation_id,),
    )
    await db.commit()


async def _generate_compilation_thumbnail(
    video_file: str, storage_root: str, compilation_id: str
) -> Optional[str]:
    """Generate thumbnail from the rendered compilation."""
    try:
        thumbnails_dir = Path(storage_root) / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumbnails_dir / f"comp_{compilation_id}.jpg"

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", video_file,
            "-ss", "00:00:01", "-vframes", "1",
            "-vf", "scale=640:-1",
            "-y", str(thumb_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

        if proc.returncode != 0 or not thumb_path.exists():
            return None
        return str(thumb_path.relative_to(storage_root))
    except Exception:
        return None


async def _get_duration(file_path: str) -> Optional[float]:
    """Get video duration using ffprobe."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0 and stdout.strip():
            return round(float(stdout.strip()), 2)
    except Exception:
        pass
    return None
