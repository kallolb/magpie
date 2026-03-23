# Magpie — Design Document

## 1. Overview

Magpie is a self-hosted web application for downloading, organizing, and streaming videos from 1000+ platforms. It provides automatic categorization, tagging, full-text search, and real-time download progress tracking.

### Key Capabilities

- Download videos from YouTube, Instagram, TikTok, Twitter/X, and 1000+ other platforms via yt-dlp
- Automatic playlist detection and batch downloading
- Duplicate detection by platform-specific video ID
- Auto-categorization based on title/description/platform/duration
- Tag-based organization with free-form tagging
- Full-text search (SQLite FTS5) across titles, descriptions, uploaders, and tags
- Real-time download progress via Server-Sent Events (SSE)
- Video streaming with HTTP range request support
- Automatic thumbnail download or generation (ffmpeg fallback)
- Webhook endpoint for chatbot integration (Telegram, Discord)
- NAS-friendly deployment with configurable storage paths

---

## 2. Architecture

```
┌─────────────┐     ┌───────────────────────────────┐     ┌────────────┐
│   Browser    │────▶│  nginx (port 3000)            │     │  Redis     │
│  React SPA   │◀────│  ├─ /         → static files  │     │  (optional)│
└─────────────┘     │  ├─ /api/*    → backend:8000  │     └────────────┘
                    │  └─ /assets/* → cached statics │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  FastAPI Backend (port 8000)   │
                    │  ├─ /api/videos/*              │
                    │  ├─ /api/downloads/*           │
                    │  ├─ /api/tags/*                │
                    │  ├─ /api/categories/*          │
                    │  ├─ /api/webhook/*             │
                    │  ├─ /api/settings, /api/health │
                    │  └─ /api/thumbnails/* (static) │
                    └───────────────────────────────┘
                          │              │
                          ▼              ▼
                    ┌──────────┐  ┌──────────────┐
                    │  SQLite  │  │  Filesystem   │
                    │  + FTS5  │  │  (videos,     │
                    │          │  │   thumbnails)  │
                    └──────────┘  └──────────────┘
```

### Technology Stack

| Layer       | Technology                                   |
|-------------|----------------------------------------------|
| Frontend    | React 18, TypeScript, Zustand, Tailwind CSS  |
| Build       | Vite 5, Node.js 20                           |
| Backend     | FastAPI, Python 3.12, Pydantic v2            |
| Database    | SQLite with WAL mode + FTS5 virtual table    |
| Downloads   | yt-dlp (1000+ platform support)              |
| Thumbnails  | httpx (download) + ffmpeg (generate)         |
| Streaming   | SSE for progress, FileResponse for video     |
| Logging     | structlog (structured JSON logging)          |
| Proxy       | nginx (dev/Docker), Caddy (production)       |
| Containers  | Docker, docker-compose                       |

---

## 3. Data Model

### 3.1 Database Schema

```
┌─────────────────────────┐       ┌──────────────────┐
│         videos          │       │       tags       │
├─────────────────────────┤       ├──────────────────┤
│ id          TEXT PK     │       │ id    INTEGER PK │
│ source_url  TEXT        │       │ name  TEXT UNIQUE│
│ platform    TEXT        │       │       NOCASE    │
│ platform_id TEXT        │       └────────┬─────────┘
│ title       TEXT        │                │
│ description TEXT        │       ┌────────┴─────────┐
│ uploader    TEXT        │       │   video_tags     │
│ upload_date TEXT        │       ├──────────────────┤
│ duration_secs INTEGER   │◀──────│ video_id TEXT FK │
│ resolution  TEXT        │       │ tag_id   INT  FK │
│ file_path   TEXT        │       │ PK(video_id,     │
│ file_size_bytes INTEGER │       │    tag_id)       │
│ thumbnail_path TEXT     │       └──────────────────┘
│ category    TEXT        │
│ status      TEXT        │       ┌──────────────────┐
│ error_message TEXT      │       │   categories     │
│ progress    REAL        │       ├──────────────────┤
│ created_at  TEXT        │       │ name    TEXT PK  │
│ updated_at  TEXT        │       │ description TEXT │
└──────────┬──────────────┘       │ created_at TEXT  │
           │                      └──────────────────┘
           │
           │  ┌──────────────────────┐
           └──│    download_log      │
              ├──────────────────────┤
              │ id INTEGER PK       │
              │ video_id TEXT FK    │
              │ triggered_by TEXT   │
              │ triggered_at TEXT   │
              │ completed_at TEXT   │
              │ status TEXT         │
              └──────────────────────┘

┌──────────────────────────────────┐
│        videos_fts (FTS5)         │
├──────────────────────────────────┤
│ title       (from videos.title)  │
│ description (from videos.desc)   │
│ uploader    (from videos.upl)    │
│ tags        (space-separated)    │
└──────────────────────────────────┘
```

### 3.2 Video Status Lifecycle

```
pending ──▶ processing ──▶ completed
                │
                ├──▶ failed
                └──▶ duplicate (record deleted)
```

- **pending**: Initial record created, awaiting download start
- **processing**: yt-dlp download in progress
- **completed**: Download finished, file on disk
- **failed**: Error occurred, error_message populated
- **duplicate**: Video already exists (by platform_id), record is deleted

### 3.3 Indexes

| Index                          | Purpose                          |
|--------------------------------|----------------------------------|
| `idx_videos_platform_id`       | Duplicate detection lookups      |
| `idx_videos_category`          | Category filtering               |
| `idx_videos_status`            | Status-based queries             |
| `idx_videos_created_at`        | Sort by date                     |
| `idx_video_tags_tag_id`        | Tag-to-video reverse lookups     |
| `idx_download_log_video_id`    | Download history per video       |

### 3.4 Default Categories

uncategorized, music, tutorials, entertainment, cooking, short-form, sports, tech, news, gaming

---

## 4. API Design

### 4.1 Videos

| Method | Endpoint                           | Description                        |
|--------|------------------------------------|------------------------------------|
| GET    | `/api/videos`                      | List videos (paginated, filterable)|
| GET    | `/api/videos/{id}`                 | Get single video with tags         |
| PUT    | `/api/videos/{id}`                 | Update title, category, tags       |
| DELETE | `/api/videos/{id}`                 | Delete video + files               |
| POST   | `/api/videos/search`               | Full-text search with filters      |
| GET    | `/api/videos/{id}/stream`          | Stream video file                  |
| POST   | `/api/videos/regenerate-thumbnails`| Generate missing thumbnails        |

### 4.2 Downloads

| Method | Endpoint                           | Description                        |
|--------|------------------------------------|------------------------------------|
| POST   | `/api/downloads`                   | Start a download                   |
| GET    | `/api/downloads/{id}`              | Get download status                |
| GET    | `/api/downloads/{id}/progress`     | SSE progress stream                |
| DELETE | `/api/downloads/{id}`              | Cancel download                    |

### 4.3 Tags & Categories

| Method | Endpoint                  | Description              |
|--------|---------------------------|--------------------------|
| GET    | `/api/tags`               | List tags with counts    |
| POST   | `/api/tags`               | Create tag               |
| DELETE | `/api/tags/{id}`          | Delete tag               |
| GET    | `/api/categories`         | List categories          |
| POST   | `/api/categories`         | Create category          |
| DELETE | `/api/categories/{name}`  | Delete category          |

### 4.4 System

| Method | Endpoint              | Description              |
|--------|-----------------------|--------------------------|
| GET    | `/api/health`         | Health check             |
| GET    | `/api/settings`       | Get configuration        |
| POST   | `/api/webhook/ingest` | Chatbot webhook          |

---

## 5. Core Flows

### 5.1 Download Pipeline

```
Client POST /api/downloads {url, category?, tags?, quality?}
    │
    ▼
Create DB record (status=pending)
    │
    ▼
Spawn asyncio background task
    │
    ▼
extract_metadata(url, flat=True)  ──── Detect playlist?
    │                                        │
    │ No                                     │ Yes
    ▼                                        ▼
extract_metadata(url, flat=False)    For each entry:
    │                                  ├─ Create DB record
    ▼                                  ├─ extract_metadata()
Check duplicate (platform_id)         ├─ _download_single_video()
    │                                  └─ Track scaled progress
    │ Exists → DELETE record, return "duplicate"
    │
    ▼
auto_categorize(title, desc, platform, duration)
    │
    ▼
download_video(url, path, quality, progress_callback)
    │
    ▼ (progress updates → DB every 2%)
    │
    ▼
save_thumbnail(url) OR generate_thumbnail(file)
    │
    ▼
UPDATE videos SET status=completed, metadata...
    │
    ▼
_apply_tags() + rebuild_fts_tags()
    │
    ▼
INSERT download_log
    │
    ▼
notify_complete() (if webhook callback)
```

### 5.2 Search Pipeline

```
Client POST /api/videos/search {query, category?, tags?}
    │
    ▼
Build FTS5 MATCH query
    │
    ▼
SELECT v.* FROM videos v
WHERE v.rowid IN (
    SELECT rowid FROM videos_fts WHERE videos_fts MATCH ?
)
    │
    ├─ AND v.category = ?           (if category filter)
    │
    ├─ AND v.id IN (                (if tags filter)
    │      SELECT vt.video_id
    │      FROM video_tags vt
    │      JOIN tags t ON vt.tag_id = t.id
    │      WHERE t.name IN (?, ?, ...)
    │  )
    │
    ▼
Return paginated VideoListResponse
```

### 5.3 Tag Update Flow

```
Client PUT /api/videos/{id} {tags: ["new-tag", "existing-tag"]}
    │
    ▼
DELETE FROM video_tags WHERE video_id = ?
    │
    ▼
For each tag name:
    ├─ INSERT OR IGNORE INTO tags (name)   ← creates if new
    ├─ SELECT id FROM tags WHERE name = ?
    └─ INSERT INTO video_tags (video_id, tag_id)
    │
    ▼
rebuild_fts_tags(video_id)  ← updates search index
    │
    ▼
Return updated VideoResponse
```

### 5.4 Thumbnail Pipeline

```
During download:
    │
    ├─ metadata has thumbnail URL?
    │     Yes → httpx.get(url) → save as {id}.jpg
    │     No ──┐
    │          ▼
    └─ ffmpeg -i video.mp4 -ss 00:00:01
         -vframes 1 -vf scale=640:-1 → {id}.jpg
    │
    ▼
Store relative path: thumbnails/{id}.jpg
    │
    ▼
API response prefixes: /api/thumbnails/{id}.jpg
    │
    ▼
nginx proxies /api/thumbnails/* → backend static mount
```

---

## 6. Frontend Architecture

### 6.1 Component Hierarchy

```
App (React Router)
├── Layout
│   ├── Header (search bar, health status)
│   ├── Sidebar (navigation)
│   └── Main Content
│       ├── Dashboard
│       │   ├── Stats Grid (videos, storage, categories, tags)
│       │   ├── Active Downloads
│       │   ├── Quick Download (DownloadForm)
│       │   └── Recent Videos (VideoGrid)
│       ├── Browse
│       │   ├── Filter Panel (category, platform, tags, sort)
│       │   ├── VideoGrid → VideoCard[]
│       │   └── Pagination
│       ├── Download
│       │   └── DownloadForm
│       │       ├── URL Input + Paste
│       │       ├── Platform Detection
│       │       ├── Category Select
│       │       ├── TagInput
│       │       ├── Quality Selector
│       │       └── Progress Bar
│       ├── Search
│       │   ├── SearchBar
│       │   └── VideoGrid (results)
│       ├── VideoView
│       │   └── VideoDetail
│       │       ├── VideoPlayer
│       │       ├── Metadata Grid
│       │       ├── Tags (TagBadge[])
│       │       ├── Edit Mode (TagInput, category select)
│       │       └── Delete Confirmation
│       └── Settings
│           ├── StorageConfig
│           └── CategoryManager
```

### 6.2 State Management (Zustand)

```
useAppStore
├── Videos State
│   ├── videos: Video[]
│   ├── totalVideos, currentPage
│   ├── videosLoading, videosError
│   └── fetchVideos(page, perPage, filters)
├── Tags State
│   ├── tags: Tag[]
│   └── fetchTags()
├── Categories State
│   ├── categories: Category[]
│   └── fetchCategories()
├── Search State
│   ├── searchQuery, searchResults[], searchTotal
│   └── fetchSearchResults(query, filters)
└── Downloads State
    ├── activeDownloads: Map<string, DownloadStatus>
    └── add/update/removeActiveDownload()
```

### 6.3 Custom Hooks

| Hook          | Purpose                                           |
|---------------|---------------------------------------------------|
| `useDownload` | Submit downloads, track SSE progress               |
| `useVideos`   | Paginated video listing with filters               |
| `useSearch`   | Debounced search with auto-navigation to /search   |

---

## 7. Infrastructure

### 7.1 Docker Services

| Service    | Image            | Port  | Purpose            |
|------------|------------------|-------|--------------------|
| frontend   | nginx:alpine     | 3000  | SPA + reverse proxy|
| backend    | python:3.12-slim | 8000  | API server         |
| redis      | redis:7-alpine   | 6379  | Task queue (opt.)  |

### 7.2 Storage Layout

```
${STORAGE_ROOT}/
├── db/
│   └── videos.db              # SQLite database
├── categories/
│   ├── uncategorized/
│   ├── music/
│   ├── tutorials/
│   ├── entertainment/
│   ├── short-form/
│   ├── tech/
│   └── ...                    # Video files organized by category
└── thumbnails/
    ├── {video_id_1}.jpg
    ├── {video_id_2}.jpg
    └── ...
```

### 7.3 Nginx Routing

| Pattern            | Destination                    | Cache     |
|--------------------|--------------------------------|-----------|
| `/api/*`           | `proxy_pass backend:8000`      | No cache  |
| `/assets/*.js/css` | Static files from build        | 1 year    |
| `/*`               | `index.html` (SPA fallback)    | No cache  |

SSE support: `proxy_buffering off`, `proxy_cache off`

### 7.4 Configuration

| Variable                    | Default          | Description                 |
|-----------------------------|------------------|-----------------------------|
| `STORAGE_ROOT`              | `./storage`      | Root storage directory      |
| `REDIS_URL`                 | `redis://...`    | Redis connection (optional) |
| `API_KEY`                   | `changeme`       | Webhook authentication key  |
| `DEFAULT_QUALITY`           | `1080`           | Download quality (pixels)   |
| `DEFAULT_FORMAT`            | `mp4`            | Download format             |
| `MAX_CONCURRENT_DOWNLOADS`  | `3`              | Concurrent download limit   |

---

## 8. Platform Support

### URL Detection

| Platform   | URL Patterns                                      | ID Extraction Regex                              |
|------------|---------------------------------------------------|--------------------------------------------------|
| YouTube    | `youtube.com/watch?v=`, `youtu.be/`               | `(?:youtube\.com/watch\?v=\|youtu\.be/)([\w-]+)` |
| Instagram  | `instagram.com/p/`, `/reel/`, `/stories/`         | `instagram\.com/(?:p\|reel\|stories)/([A-Za-z0-9_-]+)` |
| TikTok     | `tiktok.com/@user/video/`, `vm.tiktok.com/`       | `(?:tiktok\.com/.*?/video/\|vm\.tiktok\.com/)(\d+)` |
| Twitter/X  | `twitter.com/.../status/`, `x.com/.../status/`    | `(?:twitter\|x)\.com/\w+/status/(\d+)`          |
| Other      | Any `http(s)://` URL                              | Last URL path segment                            |

### Auto-Categorization Rules

| Category      | Detection Logic                                    |
|---------------|---------------------------------------------------|
| short-form    | Platform is tiktok/instagram OR duration < 60s     |
| tutorials     | Title/desc matches tutorial/how-to/learn patterns  |
| music         | Title/desc matches music/song/remix patterns       |
| cooking       | Title/desc matches recipe/cooking/chef patterns    |
| gaming        | Title/desc matches gaming/gameplay/stream patterns |
| tech          | Title/desc matches programming/code/tech patterns  |
| sports        | Title/desc matches sports/game/match patterns      |
| news          | Title/desc matches news/breaking/report patterns   |
| entertainment | Title/desc matches funny/comedy/vlog patterns      |
| uncategorized | Default fallback                                   |

---

## 9. Security Considerations

- **API Key**: Webhook endpoint protected by `X-API-Key` header
- **CORS**: Configured for all origins (development) — should be restricted in production
- **Input Sanitization**: Filenames sanitized via `safe_filename()` to prevent path traversal
- **SQL Injection**: All queries use parameterized statements via aiosqlite
- **No auth on main API**: Video listing/streaming is open — suitable for private/home network deployment
- **Thumbnail downloads**: httpx client with 10s timeout, follow redirects enabled

---

## 10. Known Limitations & Future Work

- Redis integration is scaffolded but not actively used for task queuing (uses in-memory asyncio tasks)
- No authentication on the main web UI (designed for private network use)
- Video streaming returns full FileResponse — no chunked/range-based streaming optimization
- FTS5 search uses simple tokenization — no stemming or fuzzy matching
- Single-server deployment only (no horizontal scaling)
- No video transcoding or format conversion
