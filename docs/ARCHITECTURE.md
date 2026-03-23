# Magpie Backend Architecture

## Overview

This is a production-grade FastAPI backend for downloading videos from YouTube, Instagram, TikTok, and other platforms. It features local storage, SQLite with FTS5 full-text search, automatic categorization, and a webhook API for integration with chat bots.

## Core Architecture

### Technology Stack

- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn with ASGI
- **Database**: SQLite 3 with FTS5 extension
- **Video Downloading**: yt-dlp (Python library)
- **Async**: asyncio + aiosqlite
- **Logging**: structlog
- **API Documentation**: OpenAPI/Swagger (automatic from FastAPI)

### Design Principles

1. **No External Dependencies**: Works without Redis by using in-process async tasks
2. **Local Storage**: All data is stored locally in the configured `STORAGE_ROOT`
3. **Type Safety**: Full type hints throughout (Python 3.12+)
4. **Async-First**: All I/O operations are async
5. **Production Quality**: Proper error handling, logging, and validation
6. **Extensible**: Easy to add new platforms and features

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # Settings management (Pydantic)
│   ├── database.py            # SQLite connection & initialization
│   ├── main.py                # FastAPI app factory & middleware
│   │
│   ├── models/                # Pydantic request/response models
│   │   ├── video.py
│   │   ├── tag.py
│   │   ├── category.py
│   │   └── loop_marker.py
│   │
│   ├── routers/               # API endpoint handlers
│   │   ├── downloads.py       # Download management
│   │   ├── videos.py          # Video CRUD & streaming
│   │   ├── tags.py            # Tag management
│   │   ├── categories.py      # Category management
│   │   ├── webhook.py         # Webhook integration
│   │   ├── settings.py        # Config & health endpoints
│   │   └── loop_markers.py    # A-B loop marker CRUD
│   │
│   ├── services/              # Business logic
│   │   ├── downloader.py      # yt-dlp wrapper
│   │   ├── categorizer.py     # Auto-categorization rules
│   │   ├── search.py          # FTS5 search logic
│   │   ├── thumbnail.py       # Thumbnail download/storage
│   │   └── notifier.py        # Webhook callbacks
│   │
│   ├── tasks/
│   │   └── download_task.py   # Main download pipeline
│   │
│   └── utils/                 # Utility functions
│       ├── url_parser.py      # Platform detection
│       └── file_utils.py      # File operations
│
├── tests/                      # Test suite (to be implemented)
├── migrations/                 # Schema migrations (to be implemented)
│
├── pyproject.toml             # Project metadata & dependencies
├── requirements.txt           # pip-compatible dependencies
├── Dockerfile                 # Container image
├── .env.example              # Configuration template
├── run.sh                     # Quick start script
└── USAGE.md                   # API documentation
```

## Data Flow

### Download Pipeline

1. **Request Reception** (`routers/downloads.py` or `routers/webhook.py`)
   - Validate URL and parameters
   - Create initial DB record with `status=pending`
   - Queue async task

2. **Metadata Extraction** (`services/downloader.py`)
   - Use yt-dlp to extract video info (non-blocking)
   - Get title, description, platform, duration, etc.

3. **Duplicate Check**
   - Query by `platform_id` to prevent re-downloads
   - Return error if already exists

4. **Auto-Categorization** (`services/categorizer.py`)
   - Run title/description through category rules
   - Assign category or keep user-specified one
   - Create category directory if needed

5. **File Download** (`services/downloader.py`)
   - Download video to category folder
   - Track progress via progress_callback
   - Stream to local filesystem

6. **Thumbnail Storage** (`services/thumbnail.py`)
   - Download thumbnail image
   - Save as JPEG to `storage/thumbnails/`

7. **Database Update**
   - Update video record with file paths, resolution, size
   - Set `status=completed` or `status=failed`
   - Tag application and FTS index update

8. **Notification** (`services/notifier.py`)
   - Send webhook callback to requester (if provided)
   - Log completion in `download_log` table

### Search Pipeline

1. **Query Reception** (`routers/videos.py`)
   - Validate FTS5 query and filters

2. **FTS5 Search** (`services/search.py`)
   - Execute MATCH query on FTS5 virtual table
   - Apply category/tag filters
   - Return BM25-ranked results

3. **Pagination & Response**
   - Apply LIMIT/OFFSET
   - Fetch associated tags for each video
   - Return as VideoListResponse

## Database Schema

### videos table
- `id` (TEXT PRIMARY KEY): UUID identifier
- `source_url` (TEXT): Original video URL
- `platform` (TEXT): youtube, instagram, tiktok, twitter, other
- `platform_id` (TEXT): Platform-specific video ID (for deduplication)
- `title`, `description`, `uploader`, `upload_date`: Metadata
- `duration_secs`, `resolution`: Media info
- `file_path`, `file_size_bytes`: Local storage info
- `thumbnail_path`: Relative path to thumbnail
- `category` (TEXT): Assigned category (FK to categories)
- `status` (TEXT): pending, processing, completed, failed, cancelled, duplicate
- `error_message`: Failure reason if applicable
- `progress` (REAL): Download progress 0-100
- `created_at`, `updated_at`: Timestamps

### tags table
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT UNIQUE): Tag name

### video_tags table
- `video_id`, `tag_id`: Many-to-many relationship

### categories table
- `name` (TEXT PRIMARY KEY): Category name
- `description` (TEXT): Human-readable description

### videos_fts table
- FTS5 virtual table for full-text search
- Indexes: title, description, uploader, tags

### loop_markers table
- Saved A-B loop regions per video (for music practice, study, etc.)
- `video_id`, `label`, `start_secs`, `end_secs`
- Cascade-deleted when the parent video is deleted

### download_log table
- Audit trail of download attempts
- `triggered_by`: API, webhook:source, callback:id
- `status`: success, failed

## API Endpoint Overview

### Videos API
- `GET /api/videos` - List with pagination/filtering
- `GET /api/videos/{id}` - Get details
- `PUT /api/videos/{id}` - Update metadata
- `DELETE /api/videos/{id}` - Delete with file cleanup
- `POST /api/videos/search` - Full-text search
- `GET /api/videos/{id}/stream` - Stream video file

### Downloads API
- `POST /api/downloads` - Start download
- `GET /api/downloads/{id}` - Get status
- `GET /api/downloads/{id}/progress` - SSE stream
- `DELETE /api/downloads/{id}` - Cancel

### Tags API
- `GET /api/tags` - List all
- `POST /api/tags` - Create
- `DELETE /api/tags/{id}` - Delete

### Categories API
- `GET /api/categories` - List with counts
- `POST /api/categories` - Create
- `DELETE /api/categories/{name}` - Delete

### Loop Markers API
- `GET /api/videos/{id}/loops` - List saved loops
- `POST /api/videos/{id}/loops` - Create a loop marker
- `DELETE /api/videos/{id}/loops/{loop_id}` - Delete a loop marker

### Webhook API
- `POST /api/webhook/ingest` - Universal ingestion (bot integration)

### System API
- `GET /api/health` - Health check
- `GET /api/settings` - Config (non-sensitive)

## Configuration

All settings are managed via Pydantic Settings, supporting environment variables and `.env` files:

```python
STORAGE_ROOT: str                       # Local storage path
DATABASE_PATH: str                      # Derived from STORAGE_ROOT
REDIS_URL: str                          # Optional, for future clustering
API_KEY: str                            # Secret for all endpoints
DEFAULT_QUALITY: int = 1080             # yt-dlp quality preference
DEFAULT_FORMAT: str = "mp4"             # Output format
MAX_CONCURRENT_DOWNLOADS: int = 3       # Concurrency limit
API_HOST: str = "0.0.0.0"              # Bind address
API_PORT: int = 8000                    # Bind port
```

## Key Features

### Auto-Categorization Engine
Regex-based pattern matching in title/description:
- **tutorials**: "tutorial|how to|learn|course|guide"
- **music**: "music|song|album|concert|remix"
- **cooking**: "recipe|cooking|chef|kitchen"
- **gaming**: "gameplay|playthrough|lets play"
- **tech**: "programming|code|software"
- **sports**: "football|basketball|soccer"
- **news**: "breaking|report|analysis"
- **entertainment**: "funny|comedy|vlog|reaction"
- **short-form**: Instagram/TikTok or duration < 60s

### Full-Text Search (FTS5)
- BM25 relevance ranking
- Phrase search support
- Optional category and tag filtering
- Efficient indexed queries

### Download Management
- Async background processing (no blocking)
- Server-Sent Events (SSE) for progress streaming
- Duplicate detection by platform_id
- Graceful error handling and logging
- Automatic task cleanup

### Media Handling
- yt-dlp for robust video extraction
- Thumbnail auto-download and storage
- HTTP Range request support for streaming
- Proper MIME type detection

### Webhook Integration
- Universal `/api/webhook/ingest` endpoint
- Source identification (Discord, Slack, etc.)
- Callback URL registration for notifications
- Async notification delivery

## Scalability & Performance

### SQLite Optimizations
- WAL (Write-Ahead Logging) mode for concurrent access
- PRAGMA synchronous = NORMAL for balance
- Indexed queries on frequently filtered columns
- FTS5 for efficient full-text search

### Async Design
- All I/O operations are non-blocking
- aiosqlite for async database access
- httpx for async HTTP (thumbnails, webhooks)
- asyncio for task scheduling

### Storage Efficiency
- Relative file paths in DB (portable)
- Organized by category folder
- Thumbnail compression (JPEG)
- Deduplication by platform_id

## Error Handling

### Try-Catch Strategy
- Specific exception types with meaningful messages
- Proper HTTP status codes (400, 401, 404, 409, 500)
- Detailed logging for debugging
- Graceful degradation (e.g., missing thumbnail)

### Validation
- Pydantic models for request/response validation
- API key checking on protected endpoints
- URL validation and platform detection
- File system permission checks

## Testing & Development

### Code Quality
- Full type hints (mypy compatible)
- Structured logging with JSON output
- Black code formatting (configured)
- Ruff linting rules

### Development Setup
```bash
pip install -e ".[dev]"  # Install with dev dependencies
pytest                    # Run tests
black app/              # Format code
ruff check app/         # Lint code
mypy app/               # Type check
```

## Deployment

### Docker
```bash
docker build -t video-downloader .
docker run -p 8000:8000 -v storage:/app/storage video-downloader
```

### Systemd Service (Linux)
```ini
[Unit]
Description=Magpie Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/video-downloader/backend
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name downloader.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-API-Key $http_x_api_key;

        # For SSE
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Future Enhancements

1. **Redis Integration**: Distributed task queue with RQ or Celery
2. **Database Migrations**: Alembic for schema versioning
3. **Advanced Search**: Elasticsearch for larger deployments
4. **UI Dashboard**: React/Vue frontend for management
5. **Multi-User Support**: Authentication and authorization
6. **Advanced Notifications**: Discord, Slack, Telegram integrations
7. **Quality Presets**: Save download profiles
8. **Batch Operations**: Download multiple URLs at once
9. **Streaming Optimization**: HLS transcoding options
10. **Analytics**: Download statistics and reports
