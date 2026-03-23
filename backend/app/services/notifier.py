from typing import Any, Callable, Optional

import httpx
import structlog

logger = structlog.get_logger()


_notifier: "NotificationManager | None" = None


def get_notifier() -> "NotificationManager":
    """FastAPI dependency that returns the singleton NotificationManager."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
    return _notifier


class NotificationManager:
    """Manage notifications to external services (webhooks, chat bots, etc.)."""

    def __init__(self) -> None:
        """Initialize the notification manager."""
        self.callbacks: dict[str, str] = {}

    def register_callback(self, callback_id: str, url: str) -> None:
        """Register a callback URL for notifications."""
        self.callbacks[callback_id] = url
        logger.info("callback_registered", callback_id=callback_id, url=url)

    def unregister_callback(self, callback_id: str) -> None:
        """Unregister a callback."""
        if callback_id in self.callbacks:
            del self.callbacks[callback_id]
            logger.info("callback_unregistered", callback_id=callback_id)

    async def notify_complete(
        self,
        video_id: str,
        video_info: dict[str, Any],
        callback_id: Optional[str] = None,
    ) -> None:
        """
        Notify about a completed download.

        Args:
            video_id: Video ID
            video_info: Video information dict
            callback_id: Optional callback ID to notify
        """
        if not callback_id or callback_id not in self.callbacks:
            logger.debug("no_callback_registered", video_id=video_id)
            return

        callback_url = self.callbacks[callback_id]
        payload = {
            "event": "video_downloaded",
            "video_id": video_id,
            "video": video_info,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(callback_url, json=payload)
                response.raise_for_status()
                logger.info(
                    "notification_sent",
                    video_id=video_id,
                    callback_id=callback_id,
                    status=response.status_code,
                )
        except Exception as e:
            logger.error(
                "notification_failed",
                video_id=video_id,
                callback_id=callback_id,
                error=str(e),
            )

    async def notify_error(
        self,
        video_id: str,
        error_message: str,
        callback_id: Optional[str] = None,
    ) -> None:
        """
        Notify about a download error.

        Args:
            video_id: Video ID
            error_message: Error message
            callback_id: Optional callback ID to notify
        """
        if not callback_id or callback_id not in self.callbacks:
            logger.debug("no_callback_registered", video_id=video_id)
            return

        callback_url = self.callbacks[callback_id]
        payload = {
            "event": "video_download_failed",
            "video_id": video_id,
            "error": error_message,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(callback_url, json=payload)
                response.raise_for_status()
                logger.info(
                    "error_notification_sent",
                    video_id=video_id,
                    callback_id=callback_id,
                )
        except Exception as e:
            logger.error(
                "error_notification_failed",
                video_id=video_id,
                callback_id=callback_id,
                error=str(e),
            )
