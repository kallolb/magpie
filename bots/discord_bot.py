"""
Discord Bot Adapter for SM Magpie

A thin adapter that translates Discord slash commands into calls to the
universal webhook endpoint at /api/webhook/ingest.

Setup:
    1. Create a bot at https://discord.com/developers/applications
    2. Enable MESSAGE CONTENT intent
    3. Set DISCORD_BOT_TOKEN in your .env
    4. Invite bot to your server with appropriate permissions

Commands:
    /download <url> [category] [tags]  - Download a video
    /search <query>                    - Search videos
    /recent                            - Show recent downloads
    /status <id>                       - Check download status
    /categories                        - List categories

Requirements:
    pip install discord.py httpx
"""

import os
import re
import asyncio
import logging

import httpx
import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "changeme")

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com)\S+"
)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

http_client = httpx.AsyncClient(
    base_url=API_BASE_URL,
    headers={"X-API-Key": API_KEY},
    timeout=30.0,
)


@bot.event
async def on_ready():
    logger.info(f"Discord bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")


@bot.tree.command(name="download", description="Download a video from URL")
@app_commands.describe(
    url="Video URL (YouTube, Instagram, etc.)",
    category="Category to organize the video into",
    tags="Comma-separated tags (e.g. python,tutorial)",
)
async def slash_download(
    interaction: discord.Interaction,
    url: str,
    category: str = None,
    tags: str = None,
):
    await interaction.response.defer()

    try:
        payload = {
            "source": "discord",
            "url": url,
            "callback_id": str(interaction.channel_id),
        }
        if category:
            payload["category"] = category
        if tags:
            payload["tags"] = [t.strip() for t in tags.split(",")]

        response = await http_client.post("/api/webhook/ingest", json=payload)
        response.raise_for_status()
        data = response.json()

        download_id = data.get("id", "unknown")

        embed = discord.Embed(
            title="Download Started",
            description=f"URL: {url}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="ID", value=f"`{download_id}`", inline=True)
        if category:
            embed.add_field(name="Category", value=category, inline=True)

        await interaction.followup.send(embed=embed)

        # Poll and update
        await _poll_discord(interaction, download_id)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", str(e))
        await interaction.followup.send(f"Download failed: {error_detail}")
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


async def _poll_discord(interaction: discord.Interaction, download_id: str):
    """Poll download and send completion message."""
    for _ in range(150):
        await asyncio.sleep(2)
        try:
            response = await http_client.get(f"/api/downloads/{download_id}")
            data = response.json()
            status = data.get("status")

            if status == "completed":
                video = data.get("video", {})
                embed = discord.Embed(
                    title="Download Complete",
                    description=video.get("title", "Unknown"),
                    color=discord.Color.green(),
                )
                embed.add_field(name="Category", value=video.get("category", "N/A"), inline=True)
                duration = video.get("duration_secs", 0)
                if duration:
                    embed.add_field(name="Duration", value=f"{duration // 60}m {duration % 60}s", inline=True)
                size = video.get("file_size_bytes", 0)
                if size:
                    embed.add_field(name="Size", value=f"{size / (1024*1024):.1f} MB", inline=True)

                await interaction.followup.send(embed=embed)
                return

            elif status == "failed":
                await interaction.followup.send(
                    f"Download failed: {data.get('error_message', 'Unknown error')}"
                )
                return
        except Exception:
            pass

    await interaction.followup.send(f"Download timed out. Check `/status {download_id}`")


@bot.tree.command(name="search", description="Search your video library")
@app_commands.describe(query="Search query")
async def slash_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    try:
        response = await http_client.get("/api/videos/search", params={"q": query, "per_page": 5})
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        total = data.get("total", 0)

        if not items:
            await interaction.followup.send(f'No results for "{query}"')
            return

        embed = discord.Embed(
            title=f'Search: "{query}"',
            description=f"{total} result(s) found",
            color=discord.Color.purple(),
        )
        for v in items:
            title = v.get("title", "Untitled")
            cat = v.get("category", "")
            dur = v.get("duration_secs", 0)
            dur_str = f"{dur // 60}:{dur % 60:02d}" if dur else ""
            embed.add_field(name=title, value=f"[{cat}] {dur_str}", inline=False)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Search error: {str(e)}")


@bot.tree.command(name="recent", description="Show recent downloads")
async def slash_recent(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        response = await http_client.get("/api/videos", params={"per_page": 5, "sort": "created_at", "order": "desc"})
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])

        if not items:
            await interaction.followup.send("No videos downloaded yet.")
            return

        embed = discord.Embed(title="Recent Downloads", color=discord.Color.teal())
        for v in items:
            title = v.get("title", "Untitled")
            cat = v.get("category", "")
            platform = v.get("platform", "")
            embed.add_field(name=title, value=f"[{platform}] → {cat}", inline=False)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


@bot.tree.command(name="categories", description="List video categories")
async def slash_categories(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        response = await http_client.get("/api/categories")
        response.raise_for_status()
        data = response.json()

        if not data:
            await interaction.followup.send("No categories found.")
            return

        embed = discord.Embed(title="Categories", color=discord.Color.gold())
        for cat in data:
            name = cat.get("name", "")
            count = cat.get("video_count", 0)
            embed.add_field(name=name, value=f"{count} videos", inline=True)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {str(e)}")


@bot.event
async def on_message(message: discord.Message):
    """Auto-download when a URL is posted."""
    if message.author == bot.user:
        return

    match = URL_PATTERN.search(message.content)
    if match:
        url = match.group(0)
        try:
            payload = {
                "source": "discord",
                "url": url,
                "callback_id": str(message.channel.id),
            }
            response = await http_client.post("/api/webhook/ingest", json=payload)
            response.raise_for_status()
            data = response.json()
            await message.add_reaction("⬇️")
            download_id = data.get("id", "unknown")
            await message.reply(f"Downloading... ID: `{download_id}`")
        except Exception as e:
            await message.reply(f"Download error: {str(e)}")

    await bot.process_commands(message)


def main():
    if not BOT_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set.")
        print("1. Create a bot at https://discord.com/developers/applications")
        print("2. Set DISCORD_BOT_TOKEN in your .env file")
        return

    bot.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
