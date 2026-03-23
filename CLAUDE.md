# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Magpie

A self-hosted video downloader and organizer. Downloads videos from YouTube, Instagram, and 1000+ platforms via yt-dlp, organizes them into categories, supports tagging and full-text search (SQLite FTS5), and accepts downloads from a web UI, Telegram, Discord, or webhook API.

## Architecture

- **Backend**: Python 3.12+ / FastAPI, located in `backend/`. Uses yt-dlp for downloading, aiosqlite for async SQLite access, Redis + ARQ for task queue, and structlog for logging.
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS, located in `frontend/`. Uses Zustand for state management, Axios for API calls, React Router for navigation, and Lucide for icons.
- **Bots**: Telegram and Discord bot adapters in `bots/`, which POST to the backend webhook endpoint.
- **Storage**: Videos stored in `storage/categories/<category>/`, thumbnails in `storage/thumbnails/`, SQLite DB in `storage/db/videos.db`.
- **Deployment**: Docker Compose with three services (backend, frontend, redis). Caddy reverse proxy config included. NAS storage overlay via `docker-compose.nas.yml`.

## Common Commands

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"              # includes pytest, black, ruff, mypy

uvicorn app.main:app --reload        # run dev server on :8000

pytest                               # run all tests
pytest tests/test_search.py          # run single test file
pytest tests/test_search.py::test_name -v  # run single test

black --line-length 120 app/         # format
ruff check app/                      # lint
mypy app/                            # type check
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # Vite dev server on :5173
npm run build        # tsc + vite build
npm run preview      # preview production build
```

### Docker
```bash
docker compose up -d                 # start all services
docker compose up -d --build         # rebuild and start
docker compose -f docker-compose.yml -f docker-compose.nas.yml up -d  # NAS mode
```

## Backend Structure

- `app/main.py` — FastAPI app factory, CORS, middleware, router registration, lifespan
- `app/config.py` — Pydantic Settings (env-based config), derives DB/storage paths from `STORAGE_ROOT`
- `app/database.py` — SQLite schema, init, async connection helpers (`get_db_dep`, `fetch_all`, `fetch_one`)
- `app/routers/` — API endpoints: `videos`, `downloads`, `tags`, `categories`, `webhook`, `settings`
- `app/services/` — Business logic: `downloader` (yt-dlp), `search` (FTS5), `categorizer`, `thumbnail`, `notifier`
- `app/models/` — Pydantic models for `video`, `tag`, `category`
- `app/tasks/` — ARQ background tasks (`download_task`)
- `app/utils/` — `url_parser` (platform detection), `file_utils`

## Frontend Structure

- `src/api/client.ts` — Axios-based API client, all backend calls centralized here
- `src/types/index.ts` — TypeScript interfaces matching backend models
- `src/pages/` — Route pages: Dashboard, Browse, Download, VideoView, Search, Settings
- `src/components/` — UI components organized by domain: `video/`, `tags/`, `search/`, `settings/`, `layout/`
- `src/hooks/` — Custom hooks: `useVideos`, `useTags`, `useSearch`, `useDownload`
- `src/store/index.ts` — Zustand store

## Key Conventions

- Backend line length: 120 chars (black + ruff)
- Backend uses `structlog` for all logging (not stdlib logging)
- API routes all prefixed with `/api/`
- API auth via `X-API-Key` header
- Database uses async access throughout via `aiosqlite`
- FTS index (`videos_fts`) must be kept in sync when inserting/updating videos
- Frontend uses `@/` path alias (maps to `src/`)
- Frontend uses Tailwind CSS for styling (no CSS modules)
