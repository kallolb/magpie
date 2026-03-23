"""Tests for app.services.thumbnail."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.thumbnail import save_thumbnail, generate_thumbnail


@pytest.mark.asyncio
class TestSaveThumbnail:
    """Tests for save_thumbnail()."""

    async def test_returns_none_for_empty_url(self, tmp_path):
        result = await save_thumbnail("", str(tmp_path), "vid-1")
        assert result is None

    async def test_returns_none_for_none_url(self, tmp_path):
        result = await save_thumbnail(None, str(tmp_path), "vid-1")
        assert result is None

    @patch("app.services.thumbnail.httpx.AsyncClient")
    async def test_downloads_and_saves_thumbnail(self, mock_client_cls, tmp_path):
        mock_response = MagicMock()
        mock_response.content = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # fake JPEG
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await save_thumbnail(
            "https://example.com/thumb.jpg", str(tmp_path), "vid-1"
        )

        assert result is not None
        assert result == "thumbnails/vid-1.jpg"
        assert (tmp_path / "thumbnails" / "vid-1.jpg").exists()

    @patch("app.services.thumbnail.httpx.AsyncClient")
    async def test_returns_none_on_http_error(self, mock_client_cls, tmp_path):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("404 Not Found")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await save_thumbnail(
            "https://example.com/missing.jpg", str(tmp_path), "vid-1"
        )
        assert result is None


@pytest.mark.asyncio
class TestGenerateThumbnail:
    """Tests for generate_thumbnail()."""

    async def test_returns_none_for_missing_video_file(self, tmp_path):
        result = await generate_thumbnail(
            "/nonexistent/video.mp4", str(tmp_path), "vid-1"
        )
        assert result is None

    @patch("asyncio.create_subprocess_exec")
    async def test_generates_thumbnail_from_video(self, mock_exec, tmp_path):
        # Create a fake video file
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"\x00" * 100)

        # Create the thumbnail file to simulate ffmpeg output
        thumbs_dir = tmp_path / "thumbnails"
        thumbs_dir.mkdir()
        thumb_file = thumbs_dir / "vid-1.jpg"
        thumb_file.write_bytes(b"\xff\xd8" + b"\x00" * 50)

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.wait = AsyncMock()
        mock_exec.return_value = mock_proc

        result = await generate_thumbnail(str(video_file), str(tmp_path), "vid-1")

        assert result == "thumbnails/vid-1.jpg"
        mock_exec.assert_called_once()
        # Verify ffmpeg was called with correct args
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "ffmpeg"
        assert "-vframes" in call_args
        assert "1" in call_args

    @patch("asyncio.create_subprocess_exec")
    async def test_returns_none_on_ffmpeg_failure(self, mock_exec, tmp_path):
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"\x00" * 100)

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.wait = AsyncMock()
        mock_exec.return_value = mock_proc

        result = await generate_thumbnail(str(video_file), str(tmp_path), "vid-1")
        assert result is None
