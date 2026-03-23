# Magpie

A self-hosted application that downloads videos from YouTube, Instagram, and 1000+ other platforms, organizes them into category folders, supports tagging and full-text search, and lets you trigger downloads from Telegram, Discord, or any chat bot.

## Quick Start (Local)

```bash
# 1. Clone and enter the project
cd magpie

# 2. Copy and edit config
cp .env.example .env

# 3. Start everything
docker compose up -d

# 4. Open the frontend
open http://localhost:3000
```

The API is at `http://localhost:8000` and docs at `http://localhost:8000/docs`.

## Quick Start (Without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────────────┐     ┌──────────────┐
│  React Frontend     │────▶│  FastAPI      │
│  (localhost:3000)   │     │  Backend      │
└─────────────────────┘     │  (port 8000)  │
                            │              │
┌─────────────────────┐     │  yt-dlp      │
│  Chat Bots          │────▶│  SQLite+FTS5 │
│  (Telegram/Discord) │     │  Redis/ARQ   │
└─────────────────────┘     └──────┬───────┘
                                   │
                            ┌──────▼───────┐
                            │  Storage     │
                            │  (Local/NAS) │
                            └──────────────┘
```

## Project Structure

```
magpie/
├── backend/           # FastAPI + yt-dlp + SQLite
├── frontend/          # React + TypeScript + Vite
├── bots/              # Chat bot adapters (Telegram, Discord)
├── docker-compose.yml # Local deployment
├── docker-compose.nas.yml  # NAS storage overlay
├── Caddyfile          # Production reverse proxy
├── NAS_MIGRATION.md   # Guide for moving to NAS storage
└── PLAN.md            # Full architecture plan
```

## Chat Bot Setup

### Telegram
1. Create a bot via @BotFather
2. Add `TELEGRAM_BOT_TOKEN` to `.env`
3. Run: `cd bots && python telegram_bot.py`

### Discord
1. Create app at discord.com/developers
2. Add `DISCORD_BOT_TOKEN` to `.env`
3. Run: `cd bots && python discord_bot.py`

### Any Platform
POST to `/api/webhook/ingest`:
```json
{
  "source": "my-bot",
  "url": "https://youtube.com/watch?v=...",
  "category": "tutorials",
  "tags": ["python"]
}
```

## API Examples

```bash
# Download a video
curl -X POST http://localhost:8000/api/downloads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Search
curl "http://localhost:8000/api/videos/search?q=python+tutorial" \
  -H "X-API-Key: changeme"

# List categories
curl http://localhost:8000/api/categories -H "X-API-Key: changeme"
```

## Moving to NAS Storage

See [NAS_MIGRATION.md](./NAS_MIGRATION.md) for a step-by-step guide.
