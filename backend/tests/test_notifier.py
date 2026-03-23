"""Tests for app.services.notifier."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.notifier import NotificationManager


class TestNotificationManagerCallbacks:
    """Tests for callback registration."""

    def test_register_callback(self):
        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook")
        assert "cb1" in nm.callbacks
        assert nm.callbacks["cb1"] == "https://example.com/hook"

    def test_unregister_callback(self):
        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook")
        nm.unregister_callback("cb1")
        assert "cb1" not in nm.callbacks

    def test_unregister_nonexistent_does_not_raise(self):
        nm = NotificationManager()
        nm.unregister_callback("nonexistent")

    def test_multiple_callbacks(self):
        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook1")
        nm.register_callback("cb2", "https://example.com/hook2")
        assert len(nm.callbacks) == 2


@pytest.mark.asyncio
class TestNotifyComplete:
    """Tests for notify_complete()."""

    async def test_no_callback_id_does_nothing(self):
        nm = NotificationManager()
        # Should not raise
        await nm.notify_complete("vid-1", {"title": "Test"}, callback_id=None)

    async def test_unregistered_callback_does_nothing(self):
        nm = NotificationManager()
        await nm.notify_complete("vid-1", {"title": "Test"}, callback_id="unknown")

    @patch("app.services.notifier.httpx.AsyncClient")
    async def test_sends_post_to_callback_url(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook")

        await nm.notify_complete("vid-1", {"title": "Test"}, callback_id="cb1")

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://example.com/hook"
        payload = call_args[1]["json"]
        assert payload["event"] == "video_downloaded"
        assert payload["video_id"] == "vid-1"

    @patch("app.services.notifier.httpx.AsyncClient")
    async def test_handles_post_failure_gracefully(self, mock_client_cls):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook")

        # Should not raise
        await nm.notify_complete("vid-1", {"title": "Test"}, callback_id="cb1")


@pytest.mark.asyncio
class TestNotifyError:
    """Tests for notify_error()."""

    async def test_no_callback_id_does_nothing(self):
        nm = NotificationManager()
        await nm.notify_error("vid-1", "Download failed", callback_id=None)

    @patch("app.services.notifier.httpx.AsyncClient")
    async def test_sends_error_payload(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        nm = NotificationManager()
        nm.register_callback("cb1", "https://example.com/hook")

        await nm.notify_error("vid-1", "Timeout error", callback_id="cb1")

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["event"] == "video_download_failed"
        assert payload["error"] == "Timeout error"
