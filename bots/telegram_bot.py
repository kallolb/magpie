"""
Telegram Bot Adapter for SM Magpie

A thin adapter that translates Telegram commands into calls to the
universal webhook endpoint at /api/webhook/ingest.

Setup:
    1. Create a bot via @BotFather on Telegram
    2. Set TELEGRAM_BOT_TOKEN in your .env
    3. Run this script (or add to docker-compose)

Commands:
    /download <url>                     - Download a video
    /download <url> --cat tutorials     - Download with category
    /download <url> --tag python,ai     - Download with tags
    /search <query>                     - Search videos
    /recent                             - Show recent downloads
    /status <id>                        - Check download status
    /categories                         - List categories
    /help                               - Show help

Requirements:
    pip install python-telegram-bot httpx
"""

import os
import re
import asyncio
import logging
from typing import Optional

import httpx
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "changeme")

# HTTP client for backend API
http_client = httpx.AsyncClient(
    base_url=API_BASE_URL,
    headers={"X-API-Key": API_KEY},
    timeout=30.0,
)

# URL pattern for detecting video links in messages
URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com)\S+"
)


def parse_download_args(text: str) -> dict:
    """Parse download command arguments.

    Examples:
        /download https://youtube.com/watch?v=abc
        /download https://youtube.com/watch?v=abc --cat tutorials
        /download https://youtube.com/watch?v=abc --cat tutorials --tag python,ai
    """
    parts = text.split()
    result = {"url": "", "category": None, "tags": None}

    # Find URL
    for part in parts:
        if part.startswith("http"):
            result["url"] = part
            break

    # Find --cat / --category
    for i, part in enumerate(parts):
        if part in ("--cat", "--category") and i + 1 < len(parts):
            result["category"] = parts[i + 1]

    # Find --tag / --tags
    for i, part in enumerate(parts):
        if part in ("--tag", "--tags") and i + 1 < len(parts):
            result["tags"] = [t.strip() for t in parts[i + 1].split(",")]

    return result


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "Welcome to SM Magpie!\n\n"
        "Send me a YouTube or Instagram link and I'll download it for you.\n\n"
        "Commands:\n"
        "/download <url> - Download a video\n"
        "/search <query> - Search your library\n"
        "/recent - Recent downloads\n"
        "/categories - List categories\n"
        "/help - Full help"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "SM Magpie - Commands\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Download:\n"
        "  /download <url>\n"
        "  /download <url> --cat tutorials\n"
        "  /download <url> --tag python,ai\n\n"
        "Browse:\n"
        "  /search <query>\n"
        "  /recent\n"
        "  /status <id>\n"
        "  /categories\n\n"
        "Or just paste a link and I'll download it!"
    )


async def cmd_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /download command."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /download <url> [--cat category] [--tag tag1,tag2]"
        )
        return

    args = parse_download_args(update.message.text)
    if not args["url"]:
        await update.message.reply_text("Please provide a valid URL.")
        return

    await _start_download(
        update,
        url=args["url"],
        category=args["category"],
        tags=args["tags"],
    )


async def _start_download(
    update: Update,
    url: str,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
):
    """Submit a download request to the backend."""
    msg = await update.message.reply_text(f"Fetching info for:\n{url}")

    try:
        payload = {
            "source": "telegram",
            "url": url,
            "callback_id": str(update.effective_chat.id),
        }
        if category:
            payload["category"] = category
        if tags:
            payload["tags"] = tags

        response = await http_client.post("/api/webhook/ingest", json=payload)
        response.raise_for_status()
        data = response.json()

        download_id = data.get("id", "unknown")
        await msg.edit_text(
            f"Download started!\n"
            f"ID: `{download_id}`\n"
            f"Check status: /status {download_id}",
            parse_mode="Markdown",
        )

        # Poll for completion
        asyncio.create_task(_poll_download(update, download_id, msg))

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", str(e))
        await msg.edit_text(f"Download failed: {error_detail}")
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")


async def _poll_download(update: Update, download_id: str, status_msg):
    """Poll download status and send updates."""
    last_progress = -1

    for _ in range(300):  # Max 5 minutes of polling
        await asyncio.sleep(2)

        try:
            response = await http_client.get(f"/api/downloads/{download_id}")
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "unknown")
            progress = int(data.get("progress", 0))

            if status == "completed":
                video = data.get("video", {})
                title = video.get("title", "Unknown")
                category = video.get("category", "uncategorized")
                duration = video.get("duration_secs", 0)
                resolution = video.get("resolution", "")
                file_size = video.get("file_size_bytes", 0)

                size_mb = f"{file_size / (1024 * 1024):.1f} MB" if file_size else "N/A"
                dur_str = f"{duration // 60}m {duration % 60}s" if duration else "N/A"

                await status_msg.edit_text(
                    f"Download complete!\n\n"
                    f"Title: {title}\n"
                    f"Category: {category}\n"
                    f"Duration: {dur_str}\n"
                    f"Quality: {resolution}\n"
                    f"Size: {size_mb}"
                )
                return

            elif status == "failed":
                error = data.get("error_message", "Unknown error")
                await status_msg.edit_text(f"Download failed: {error}")
                return

            elif progress != last_progress and progress > 0:
                bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
                await status_msg.edit_text(
                    f"Downloading... {progress}%\n[{bar}]"
                )
                last_progress = progress

        except Exception:
            pass  # Silently retry

    await status_msg.edit_text("Download timed out. Check /status " + download_id)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command."""
    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args)

    try:
        response = await http_client.get(
            "/api/videos/search",
            params={"q": query, "per_page": 5},
        )
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:
            await update.message.reply_text(f'No results for "{query}"')
            return

        lines = [f'Search: "{query}" ({total} results)\n']
        for i, v in enumerate(items, 1):
            title = v.get("title", "Untitled")
            category = v.get("category", "")
            duration = v.get("duration_secs", 0)
            dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else ""
            lines.append(f"{i}. {title}\n   [{category}] {dur_str}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        await update.message.reply_text(f"Search error: {str(e)}")


async def cmd_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /recent command."""
    try:
        response = await http_client.get(
            "/api/videos",
            params={"page": 1, "per_page": 5, "sort": "created_at", "order": "desc"},
        )
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            await update.message.reply_text("No videos downloaded yet.")
            return

        lines = ["Recent Downloads:\n"]
        for i, v in enumerate(items, 1):
            title = v.get("title", "Untitled")
            category = v.get("category", "")
            platform = v.get("platform", "")
            lines.append(f"{i}. {title}\n   [{platform}] → {category}")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status <id> command."""
    if not context.args:
        await update.message.reply_text("Usage: /status <download_id>")
        return

    download_id = context.args[0]

    try:
        response = await http_client.get(f"/api/downloads/{download_id}")
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        progress = data.get("progress", 0)

        text = f"Download {download_id}\nStatus: {status}"
        if status == "downloading":
            text += f"\nProgress: {progress:.0f}%"
        elif status == "completed" and data.get("video"):
            text += f"\nTitle: {data['video'].get('title', '')}"
        elif status == "failed":
            text += f"\nError: {data.get('error_message', 'Unknown')}"

        await update.message.reply_text(text)

    except httpx.HTTPStatusError:
        await update.message.reply_text(f"Download {download_id} not found.")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def cmd_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /categories command."""
    try:
        response = await http_client.get("/api/categories")
        response.raise_for_status()
        data = response.json()

        if not data:
            await update.message.reply_text("No categories found.")
            return

        lines = ["Categories:\n"]
        for cat in data:
            name = cat.get("name", "")
            count = cat.get("video_count", 0)
            lines.append(f"  • {name} ({count} videos)")

        await update.message.reply_text("\n".join(lines))

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain messages that contain video URLs."""
    text = update.message.text or ""
    match = URL_PATTERN.search(text)
    if match:
        url = match.group(0)
        await _start_download(update, url=url)


def main():
    """Run the Telegram bot."""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set.")
        print("1. Talk to @BotFather on Telegram to create a bot")
        print("2. Set TELEGRAM_BOT_TOKEN in your .env file")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("download", cmd_download))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("recent", cmd_recent))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("categories", cmd_categories))

    # Handle plain URLs (auto-download)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message))

    logger.info("Telegram bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
