# Magpie — Architecture & Implementation Plan

## 1. Overview

A self-hosted application that downloads videos from YouTube and Instagram (extensible to other platforms), organizes them into category folders, supports tagging and full-text search, and exposes a webhook API so any chat bot (Telegram, Discord, Slack) can trigger downloads by simply sending a link.

Everything — videos, thumbnails, and the search index — lives under a single **configurable storage root** (e.g. an NFS-mounted NAS path), making backups trivial.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat Clients                         │
│  (Telegram Bot · Discord Bot · Slack Bot · CLI · curl)      │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTPS / Webhook
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐  │
│  │ Download  │  │ Metadata │  │  Search   │  │  Webhook  │  │
│  │  Engine   │  │ & Tagging│  │  (FTS5)   │  │  Gateway  │  │
│  │ (yt-dlp) │  │  Service │  │           │  │           │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └─────┬─────┘  │
│       │              │              │              │         │
│       ▼              ▼              ▼              │         │
│  ┌─────────────────────────────────────────┐      │         │
│  │  Background Task Queue (asyncio / ARQ)  │◄─────┘         │
│  └─────────────────────────────────────────┘                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Configurable Storage Root                   │
│                  (NAS / Local / S3-fuse)                     │
│                                                             │
│  /storage-root/                                             │
│  ├── db/                                                    │
│  │   └── videos.db          ← SQLite + FTS5 index          │
│  ├── thumbnails/                                            │
│  │   └── {video_id}.jpg                                     │
│  └── videos/                                                │
│      ├── music/                                             │
│      ├── tutorials/                                         │
│      ├── entertainment/                                     │
│      ├── cooking/                                           │
│      └── uncategorized/                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              React + TypeScript Frontend (SPA)               │
│                                                             │
│  Dashboard · Browse/Search · Video Player · Tag Manager     │
│  Category Manager · Settings (storage path, chat bots)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack Summary

| Layer            | Technology                          | Rationale                                                  |
|------------------|-------------------------------------|------------------------------------------------------------|
| Frontend         | React 18 + TypeScript + Vite        | Fast dev cycle, rich ecosystem, easy to containerize       |
| UI Components    | shadcn/ui + Tailwind CSS            | Clean, accessible components without heavy dependencies    |
| Backend          | Python 3.12 + FastAPI               | Async-native, great typing, native yt-dlp integration     |
| Download Engine  | yt-dlp (Python library)             | Best-in-class extractor for YouTube, Instagram, 1000+ sites|
| Task Queue       | ARQ (async Redis queue) or Celery   | Background download jobs, retries, progress tracking       |
| Message Broker   | Redis                               | Lightweight, doubles as cache and pub/sub for progress     |
| Database         | SQLite 3.40+ with FTS5              | Zero-dependency, file-based, lives on NAS alongside videos |
| Search           | SQLite FTS5 (full-text search)      | Built into the DB file, no extra service to run            |
| Containerization | Docker + Docker Compose             | Single `docker compose up` to launch everything            |
| Reverse Proxy    | Caddy or Traefik                    | Auto-TLS for chat bot webhooks, simple config              |

---

## 4. Data Model

### 4.1 SQLite Schema

```sql
-- Core videos table
CREATE TABLE videos (
    id              TEXT PRIMARY KEY,     -- UUID or yt-dlp video ID
    source_url      TEXT NOT NULL,
    platform        TEXT NOT NULL,        -- 'youtube', 'instagram', etc.
    platform_id     TEXT,                 -- Platform-specific video ID
    title           TEXT NOT NULL,
    description     TEXT,
    uploader        TEXT,
    upload_date     TEXT,                 -- ISO 8601
    duration_secs   INTEGER,
    resolution      TEXT,                 -- e.g. '1080p'
    file_path       TEXT NOT NULL,        -- Relative to storage root
    file_size_bytes INTEGER,
    thumbnail_path  TEXT,                 -- Relative to storage root
    category        TEXT NOT NULL DEFAULT 'uncategorized',
    status          TEXT NOT NULL DEFAULT 'pending',
                    -- 'pending','downloading','completed','failed'
    error_message   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tags (many-to-many)
CREATE TABLE tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE video_tags (
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (video_id, tag_id)
);

-- Categories (predefined + user-created)
CREATE TABLE categories (
    name        TEXT PRIMARY KEY,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Full-text search index
CREATE VIRTUAL TABLE videos_fts USING fts5(
    title,
    description,
    uploader,
    tags,           -- Denormalized comma-separated tag names
    content=videos,
    content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER videos_ai AFTER INSERT ON videos BEGIN
    INSERT INTO videos_fts(rowid, title, description, uploader, tags)
    VALUES (new.rowid, new.title, new.description, new.uploader, '');
END;

CREATE TRIGGER videos_ad AFTER DELETE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, title, description, uploader, tags)
    VALUES ('delete', old.rowid, old.title, old.description, old.uploader, '');
END;

CREATE TRIGGER videos_au AFTER UPDATE ON videos BEGIN
    INSERT INTO videos_fts(videos_fts, rowid, title, description, uploader, tags)
    VALUES ('delete', old.rowid, old.title, old.description, old.uploader, '');
    INSERT INTO videos_fts(rowid, title, description, uploader, tags)
    VALUES (new.rowid, new.title, new.description, new.uploader, '');
END;

-- Download history / audit log
CREATE TABLE download_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL REFERENCES videos(id),
    triggered_by TEXT,          -- 'web', 'telegram', 'discord', 'api'
    triggered_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status       TEXT NOT NULL   -- 'success', 'failed', 'retried'
);
```

### 4.2 Key Design Decisions

- **All paths stored as relative** to `STORAGE_ROOT` so the DB stays valid if the NAS mount point changes.
- **FTS5 tags column is denormalized** — rebuilt on tag changes — for fast full-text queries across all fields.
- **`id` is a UUID** assigned by the app, while `platform_id` holds the YouTube/Instagram native ID for dedup.

---

## 5. Backend Architecture (FastAPI)

### 5.1 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, lifespan events
│   ├── config.py               # Pydantic Settings (env-based config)
│   ├── database.py             # SQLite connection, migrations
│   ├── models/
│   │   ├── video.py            # Pydantic models for Video
│   │   ├── tag.py
│   │   └── category.py
│   ├── routers/
│   │   ├── videos.py           # CRUD + search endpoints
│   │   ├── downloads.py        # Trigger download, check status
│   │   ├── tags.py             # Tag management
│   │   ├── categories.py       # Category management
│   │   ├── webhook.py          # Incoming webhook for chat bots
│   │   └── settings.py         # Runtime config (storage path, etc.)
│   ├── services/
│   │   ├── downloader.py       # yt-dlp wrapper, format selection
│   │   ├── categorizer.py      # Auto-categorization logic
│   │   ├── search.py           # FTS5 query builder
│   │   ├── thumbnail.py        # Thumbnail extraction/storage
│   │   └── notifier.py         # Send status back to chat bots
│   ├── tasks/
│   │   ├── worker.py           # ARQ worker setup
│   │   └── download_task.py    # Background download job
│   └── utils/
│       ├── url_parser.py       # Detect platform from URL
│       └── file_utils.py       # Safe filename, path helpers
├── migrations/                 # SQL migration scripts
├── tests/
├── Dockerfile
├── pyproject.toml
└── alembic.ini                 # (or simple migration runner)
```

### 5.2 API Endpoints

```
POST   /api/downloads           # Submit a URL for download
GET    /api/downloads/{id}      # Check download status/progress
DELETE /api/downloads/{id}      # Cancel a pending download

GET    /api/videos              # List videos (paginated, filterable)
GET    /api/videos/{id}         # Video detail + metadata
PUT    /api/videos/{id}         # Update title, category, tags
DELETE /api/videos/{id}         # Delete video + file

GET    /api/videos/search?q=    # Full-text search
GET    /api/videos/stream/{id}  # Stream video file (range requests)

GET    /api/tags                # List all tags with usage counts
POST   /api/tags                # Create a tag
DELETE /api/tags/{id}           # Delete a tag

GET    /api/categories          # List categories
POST   /api/categories          # Create category (creates folder)
DELETE /api/categories/{name}   # Delete category

POST   /api/webhook/ingest      # Universal chat bot webhook
GET    /api/settings            # Current config
PUT    /api/settings            # Update storage path, etc.
GET    /api/health              # Health check for container orchestration
```

### 5.3 Download Pipeline (Step by Step)

```
1. URL arrives (via frontend, API, or chat webhook)
         │
2. url_parser.py detects platform (youtube/instagram/other)
         │
3. yt-dlp extracts metadata WITHOUT downloading
   (title, description, uploader, duration, thumbnail URL, formats)
         │
4. Dedup check: does platform_id already exist in DB?
   ├── Yes → return existing record (or offer re-download)
   └── No  → continue
         │
5. Create DB record with status='pending'
         │
6. Enqueue background task → ARQ/Redis
         │
7. Worker picks up job:
   a. Update status → 'downloading'
   b. yt-dlp downloads best format (configurable quality)
   c. Download thumbnail
   d. Determine category:
      - If user specified one → use it
      - Else → auto-categorize (keyword matching on title/tags)
   e. Move file to: {STORAGE_ROOT}/videos/{category}/{safe_filename}.mp4
   f. Move thumbnail to: {STORAGE_ROOT}/thumbnails/{video_id}.jpg
   g. Update DB record with file paths, resolution, size
   h. Update status → 'completed'
   i. Update FTS5 index
   j. Notify requester (chat bot callback, SSE to frontend)
         │
8. Frontend receives SSE event, updates UI in real time
```

### 5.4 Auto-Categorization Strategy

The categorizer works in layers:

1. **User-specified category** (highest priority) — passed in the download request.
2. **Keyword rules** — configurable mapping stored in the DB, e.g.:
   - `"tutorial|how to|learn|course"` → `tutorials`
   - `"recipe|cooking|chef|kitchen"` → `cooking`
   - `"music|song|album|concert"` → `music`
3. **Platform heuristic** — Instagram Reels → `short-form`, YouTube Shorts → `short-form`.
4. **Fallback** → `uncategorized` (user can recategorize later in the UI).

Future enhancement: use a small local LLM or embedding model for smarter categorization.

---

## 6. Frontend Architecture (React + TypeScript)

### 6.1 Project Structure

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   └── client.ts           # Axios/fetch wrapper, typed endpoints
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx     # Category tree, navigation
│   │   │   ├── Header.tsx      # Search bar, user menu
│   │   │   └── Layout.tsx
│   │   ├── video/
│   │   │   ├── VideoCard.tsx   # Thumbnail, title, tags, duration
│   │   │   ├── VideoGrid.tsx   # Responsive grid of VideoCards
│   │   │   ├── VideoPlayer.tsx # Embedded player (video.js or native)
│   │   │   ├── VideoDetail.tsx # Full metadata, edit tags/category
│   │   │   └── DownloadForm.tsx# URL input + options
│   │   ├── search/
│   │   │   ├── SearchBar.tsx
│   │   │   └── SearchResults.tsx
│   │   ├── tags/
│   │   │   ├── TagBadge.tsx
│   │   │   ├── TagInput.tsx    # Autocomplete tag selector
│   │   │   └── TagManager.tsx
│   │   └── settings/
│   │       ├── StorageConfig.tsx
│   │       └── CategoryManager.tsx
│   ├── hooks/
│   │   ├── useVideos.ts
│   │   ├── useSearch.ts
│   │   ├── useDownload.ts      # SSE subscription for progress
│   │   └── useTags.ts
│   ├── pages/
│   │   ├── Dashboard.tsx       # Recent downloads, stats
│   │   ├── Browse.tsx          # Video grid with filters
│   │   ├── VideoView.tsx       # Single video page
│   │   ├── Search.tsx          # Search results page
│   │   └── Settings.tsx        # Config page
│   ├── store/                  # Zustand or React Query cache
│   └── types/
│       └── index.ts            # Shared TypeScript interfaces
├── Dockerfile
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 6.2 Key UI Screens

| Screen        | Description                                                              |
|---------------|--------------------------------------------------------------------------|
| Dashboard     | Recent downloads with progress bars, quick stats (total videos, storage used) |
| Download      | URL input field, optional category/tag picker, quality selector, submit button |
| Browse        | Grid/list view of videos, filterable by category, tags, platform, date   |
| Video Detail  | Video player, metadata panel, tag editor, category reassignment, delete  |
| Search        | Full-text search bar with instant results, highlighted matches           |
| Settings      | Storage root path, manage categories, manage chat bot integrations       |

### 6.3 Real-Time Progress

Use **Server-Sent Events (SSE)** from FastAPI to push download progress to the frontend:

```
GET /api/downloads/{id}/progress  →  SSE stream

Events:
  event: progress
  data: {"percent": 45, "speed": "2.3 MB/s", "eta": "12s"}

  event: completed
  data: {"video_id": "abc123", "file_path": "..."}

  event: error
  data: {"message": "Video unavailable"}
```

---

## 7. Chat Bot Integration (Webhook Gateway)

### 7.1 Architecture

Rather than building platform-specific bots into the core, the app exposes a **universal webhook endpoint** and uses thin adapter layers:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Telegram Bot │     │ Discord Bot  │     │  Slack Bot   │
│  (adapter)   │     │  (adapter)   │     │  (adapter)   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                 POST /api/webhook/ingest
                 {
                   "source": "telegram",
                   "url": "https://youtube.com/watch?v=...",
                   "category": "tutorials",   // optional
                   "tags": ["python", "ai"],  // optional
                   "callback_id": "chat_12345"
                 }
```

### 7.2 Chat Bot Command Interface

Each bot adapter translates platform-specific commands into the universal format:

```
/download <url>                          → Download with auto-categorize
/download <url> --cat tutorials          → Download into 'tutorials'
/download <url> --tag python,fastapi     → Download with tags
/search <query>                          → Search videos, return top 5
/recent                                  → Show last 5 downloads
/status <id>                             → Check download progress
/categories                              → List available categories
```

### 7.3 Notification Flow

When a download completes, the notifier service sends a callback to the originating chat:

```
✅ Download complete!
📹 "FastAPI Full Course 2026"
📂 tutorials/fastapi-full-course-2026.mp4
🏷️ python, fastapi, tutorial
⏱️ 2h 15m · 1080p · 1.8 GB
```

---

## 8. Storage Layout

```
{STORAGE_ROOT}/                          # User-configurable (e.g. /mnt/nas/videos)
├── db/
│   ├── videos.db                        # SQLite database + FTS5 index
│   └── videos.db-wal                    # WAL mode for concurrent reads
├── thumbnails/
│   ├── {video_id}.jpg
│   └── ...
├── videos/
│   ├── music/
│   │   ├── song-title-abc123.mp4
│   │   └── ...
│   ├── tutorials/
│   │   ├── fastapi-full-course-def456.mp4
│   │   └── ...
│   ├── entertainment/
│   ├── cooking/
│   ├── short-form/
│   └── uncategorized/
└── config/
    ├── categories.json                  # Category → keyword rules
    └── settings.json                    # Runtime settings backup
```

---

## 9. Containerization & Deployment

### 9.1 Docker Compose

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - STORAGE_ROOT=/data
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=sqlite:///data/db/videos.db
    volumes:
      - video-storage:/data          # Mount your NAS here
    depends_on:
      - redis
    restart: unless-stopped

  worker:
    build: ./backend
    command: arq app.tasks.worker.WorkerSettings
    environment:
      - STORAGE_ROOT=/data
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=sqlite:///data/db/videos.db
    volumes:
      - video-storage:/data
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

  # Optional: reverse proxy for HTTPS + bot webhooks
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
    restart: unless-stopped

volumes:
  video-storage:
    driver: local
    driver_opts:
      type: nfs                        # Example: NAS via NFS
      o: addr=192.168.1.100,rw
      device: ":/volume1/videos"
  redis-data:
  caddy-data:
```

### 9.2 Single-Command Deployment

```bash
# Clone and start
git clone https://github.com/you/magpie.git
cd magpie

# Configure storage (edit .env)
echo "STORAGE_ROOT=/mnt/nas/videos" > .env

# Launch
docker compose up -d
```

---

## 10. Implementation Phases

### Phase 1 — Core Download Engine (Week 1–2)

- [ ] Set up FastAPI project scaffold with config management
- [ ] Implement SQLite database layer with migrations
- [ ] Build yt-dlp download service (YouTube + Instagram)
- [ ] Implement background task queue with ARQ + Redis
- [ ] Create download API endpoints (submit, status, cancel)
- [ ] Add file organization logic (category folders, safe filenames)
- [ ] Write unit tests for downloader and URL parser
- [ ] Create Dockerfile for backend

### Phase 2 — Metadata, Tagging & Search (Week 3)

- [ ] Implement FTS5 search index with sync triggers
- [ ] Build tag CRUD operations and video-tag associations
- [ ] Create category management (CRUD + folder creation)
- [ ] Implement auto-categorization with keyword rules
- [ ] Build search API with relevance ranking and filters
- [ ] Add thumbnail extraction and storage
- [ ] Write integration tests for the full download-to-search pipeline

### Phase 3 — Frontend (Week 4–5)

- [ ] Set up React + Vite + TypeScript + Tailwind project
- [ ] Build layout shell (sidebar, header, routing)
- [ ] Implement download form with URL input and options
- [ ] Build video grid/list browse page with pagination
- [ ] Create video detail page with player and metadata editor
- [ ] Implement search UI with instant results
- [ ] Add SSE-based real-time download progress
- [ ] Build settings page (storage, categories)
- [ ] Create Dockerfile for frontend (Nginx-served static build)

### Phase 4 — Chat Bot Integration (Week 6)

- [ ] Build universal webhook gateway endpoint
- [ ] Create Telegram bot adapter (most common first)
- [ ] Implement command parsing (/download, /search, /status)
- [ ] Add completion notification callback system
- [ ] Write adapter template for Discord and Slack
- [ ] Document how to add new chat platform adapters

### Phase 5 — Containerization & Hardening (Week 7)

- [ ] Write Docker Compose with all services
- [ ] Add NFS/CIFS volume mount examples for NAS
- [ ] Configure Caddy for HTTPS and webhook routing
- [ ] Add health checks and graceful shutdown
- [ ] Implement rate limiting and basic auth (API key)
- [ ] Add download retry logic and error recovery
- [ ] Write deployment documentation

### Phase 6 — Polish & Extensions (Week 8+)

- [ ] Add bulk download (playlists, channels)
- [ ] Implement video quality/format preferences
- [ ] Add storage usage dashboard and cleanup tools
- [ ] Support additional platforms via yt-dlp extractors
- [ ] Optional: LLM-based auto-tagging and categorization
- [ ] Optional: RSS feed monitoring for auto-download
- [ ] Optional: mobile-responsive PWA mode

---

## 11. Configuration

All configuration via environment variables (12-factor app):

```env
# Storage
STORAGE_ROOT=/mnt/nas/videos        # Where everything lives
MAX_STORAGE_GB=500                   # Optional storage cap

# Server
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your-secret-api-key          # Simple auth for API + bots

# Redis
REDIS_URL=redis://redis:6379

# Download defaults
DEFAULT_QUALITY=1080                 # Max resolution
DEFAULT_FORMAT=mp4                   # Preferred container
MAX_CONCURRENT_DOWNLOADS=3

# Chat bots (each optional)
TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...
SLACK_BOT_TOKEN=...
SLACK_SIGNING_SECRET=...
```

---

## 12. Security Considerations

- **API key authentication** on all endpoints (simple bearer token for v1).
- **Rate limiting** on download endpoint to prevent abuse.
- **Input validation** — sanitize URLs, filenames, and search queries.
- **No shell injection** — yt-dlp is called as a Python library, never via subprocess with string interpolation.
- **SQLite WAL mode** for safe concurrent reads from frontend + worker.
- **HTTPS via Caddy** for chat bot webhooks (Telegram requires HTTPS).
- Future: add OAuth2/OIDC for multi-user support.

---

## 13. Monitoring & Observability

- **Health endpoint** (`/api/health`) for Docker health checks.
- **Structured logging** (JSON) via Python `structlog`.
- **Download metrics**: success/failure rate, avg download time, storage usage.
- **Optional**: Prometheus metrics endpoint + Grafana dashboard.
- **SQLite PRAGMA stats** for DB performance monitoring.
