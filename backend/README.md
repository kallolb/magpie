# Magpie Backend

A production-grade FastAPI backend for downloading videos from YouTube, Instagram, TikTok, Twitter, and other platforms. Features local storage, SQLite FTS5 full-text search, automatic categorization, and webhook API for chatbot integration.

## Features

✨ **Core Capabilities**
- Download videos from multiple platforms (YouTube, Instagram, TikTok, Twitter, etc.)
- Automatic video categorization based on content
- Full-text search with FTS5 and BM25 ranking
- Tag management and filtering
- Local file storage with relative paths
- HTTP Range request support for video streaming
- Server-Sent Events (SSE) for real-time progress updates
- Webhook API for chatbot/bot integration
- Duplicate detection by platform ID

🔧 **Architecture**
- **Framework**: FastAPI with Uvicorn
- **Database**: SQLite 3 with FTS5 extension
- **Async**: asyncio + aiosqlite (non-blocking I/O)
- **Video**: yt-dlp (Python library, not subprocess)
- **Logging**: structlog with JSON output
- **Python**: 3.12+ with full type hints

⚡ **Performance**
- SQLite WAL mode for concurrent access
- Indexed queries on filtered columns
- In-process async task queue (no Redis required)
- Efficient FTS5 full-text search

🎯 **Zero External Dependencies**
- Works without Redis (graceful fallback)
- All data stored locally
- No cloud services required
- Suitable for self-hosted deployments

## Quick Start

### Installation

```bash
# Clone the repository
cd backend

# Install dependencies
pip install -r requirements.txt

# Or use pyproject.toml
pip install -e .
```

### Configuration

```bash
# Create .env from template
cp .env.example .env

# Edit .env with your settings
nano .env
```

Default `.env`:
```env
STORAGE_ROOT=./storage
API_KEY=changeme
DEFAULT_QUALITY=1080
DEFAULT_FORMAT=mp4
MAX_CONCURRENT_DOWNLOADS=3
API_HOST=0.0.0.0
API_PORT=8000
```

### Run Locally

```bash
# Development with auto-reload
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the provided script
chmod +x run.sh
./run.sh
```

Visit: http://localhost:8000/docs (Swagger UI)

### Docker

```bash
# Build image
docker build -t video-downloader .

# Run container
docker run -p 8000:8000 -v $(pwd)/storage:/app/storage video-downloader

# With custom env
docker run -p 8000:8000 \
  -e API_KEY=your-secret \
  -e STORAGE_ROOT=/data \
  -v /data:/app/storage \
  video-downloader
```

## API Examples

### Start a Download

```bash
curl -X POST http://localhost:8000/api/downloads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "category": "music",
    "tags": ["classic", "80s"],
    "quality": 1080
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Download queued successfully"
}
```

### Stream Progress

```bash
curl -N http://localhost:8000/api/downloads/{video_id}/progress \
  -H "X-API-Key: changeme"
```

Server-Sent Events output:
```
data: {"status": "processing", "progress": 0}
data: {"status": "processing", "progress": 25}
data: {"status": "processing", "progress": 50}
data: {"status": "completed", "progress": 100}
```

### Search Videos

```bash
curl -X POST http://localhost:8000/api/videos/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "query": "tutorial python",
    "category": "tech",
    "page": 1,
    "per_page": 20
  }'
```

### Stream Video

```bash
curl -H "X-API-Key: changeme" \
  http://localhost:8000/api/videos/{video_id}/stream \
  -o downloaded_video.mp4
```

### List Videos

```bash
curl http://localhost:8000/api/videos?category=music&page=1&per_page=20 \
  -H "X-API-Key: changeme"
```

### Webhook Integration

```bash
# Trigger download from external source (Discord bot, etc)
curl -X POST http://localhost:8000/api/webhook/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "source": "discord_bot",
    "url": "https://www.youtube.com/watch?v=...",
    "category": "music",
    "tags": ["shared"],
    "callback_id": "discord_user_123"
  }'
```

## Documentation

- **[USAGE.md](USAGE.md)** - Detailed API reference and examples
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and technical details
- **[.env.example](.env.example)** - Configuration template

## File Structure

```
backend/
├── app/
│   ├── config.py              # Settings management
│   ├── database.py            # SQLite setup
│   ├── main.py                # FastAPI application
│   ├── models/                # Request/response schemas
│   ├── routers/               # API endpoints
│   ├── services/              # Business logic
│   ├── tasks/                 # Download pipeline
│   └── utils/                 # Helper functions
├── pyproject.toml             # Project config
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container image
├── run.sh                      # Quick start script
├── USAGE.md                    # API documentation
└── ARCHITECTURE.md            # Technical design
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/downloads` | Start a download |
| GET | `/api/downloads/{id}` | Get download status |
| GET | `/api/downloads/{id}/progress` | Stream progress (SSE) |
| DELETE | `/api/downloads/{id}` | Cancel download |
| GET | `/api/videos` | List videos |
| GET | `/api/videos/{id}` | Get video details |
| PUT | `/api/videos/{id}` | Update video metadata |
| DELETE | `/api/videos/{id}` | Delete video |
| POST | `/api/videos/search` | Full-text search |
| GET | `/api/videos/{id}/stream` | Stream video file |
| GET | `/api/tags` | List tags |
| POST | `/api/tags` | Create tag |
| DELETE | `/api/tags/{id}` | Delete tag |
| GET | `/api/categories` | List categories |
| POST | `/api/categories` | Create category |
| DELETE | `/api/categories/{name}` | Delete category |
| POST | `/api/webhook/ingest` | Webhook integration |
| GET | `/api/health` | Health check |
| GET | `/api/settings` | Get settings |

All endpoints require `X-API-Key` header (except `/api/health`).

## Database Schema

### videos
Main video records with metadata and file paths

### tags
Available tags with many-to-many relationship to videos

### categories
Video categories (music, tutorials, tech, etc.)

### videos_fts
Full-text search index using SQLite FTS5

### download_log
Audit trail of download attempts

## Features in Detail

### Auto-Categorization
Videos are automatically categorized based on title/description patterns:
- **tutorials** - detected by: "tutorial", "how to", "learn", "course", "guide"
- **music** - detected by: "music", "song", "album", "concert", "remix"
- **cooking** - detected by: "recipe", "cooking", "chef", "kitchen"
- **gaming** - detected by: "gameplay", "playthrough", "lets play"
- **tech** - detected by: "programming", "code", "software", "hardware"
- **sports** - detected by: "football", "basketball", "soccer", "match"
- **news** - detected by: "breaking", "report", "analysis"
- **entertainment** - detected by: "funny", "comedy", "prank", "vlog"
- **short-form** - videos from Instagram/TikTok or < 60 seconds

### Platform Detection
Automatic detection of:
- YouTube (youtube.com, youtu.be)
- Instagram (instagram.com)
- TikTok (tiktok.com)
- Twitter/X (twitter.com, x.com)
- Others (generic fallback)

### Full-Text Search
- BM25 relevance ranking
- Phrase search support
- Filter by category and tags
- Pagination support

### Progress Tracking
- Real-time download progress via SSE
- Stored in database for persistence
- HTTP Range request support for video streaming

## Storage Structure

```
storage/
├── categories/
│   ├── music/
│   │   ├── Song Title 1.mp4
│   │   └── Song Title 2.mp4
│   ├── tutorials/
│   │   └── Python Tutorial.mp4
│   └── uncategorized/
├── thumbnails/
│   ├── uuid1.jpg
│   └── uuid2.jpg
└── db/
    └── videos.db
```

All paths in the database are relative to `STORAGE_ROOT` for portability.

## Configuration

Edit `.env` to customize behavior:

```env
# Storage location
STORAGE_ROOT=./storage

# Security
API_KEY=your-secret-key-here

# Download preferences
DEFAULT_QUALITY=1080          # 720, 1080, 2160, etc.
DEFAULT_FORMAT=mp4           # mp4, webm, etc.
MAX_CONCURRENT_DOWNLOADS=3   # Parallel downloads

# Server
API_HOST=0.0.0.0            # Bind address
API_PORT=8000               # Bind port

# Optional: Redis for distributed queue
REDIS_URL=redis://localhost:6379
```

## Development

### Setup Dev Environment

```bash
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black app/

# Lint
ruff check app/

# Type check
mypy app/

# Run tests (when tests are added)
pytest
```

### Verify Structure

```bash
python verify_structure.py
```

## Performance Notes

- **Database**: SQLite WAL mode allows concurrent reads/writes
- **FTS5**: Indexed full-text search for fast queries
- **Async**: All I/O operations are non-blocking
- **Tasks**: In-process task queue (no external broker needed)
- **Storage**: Relative file paths for portability

## Security

- API key validation on all protected endpoints
- Input validation via Pydantic models
- Secure file operations (sanitized filenames)
- Proper error messages without exposing internals
- CORS configured for local development

## Troubleshooting

### Port Already in Use
```bash
# Use different port
python -m uvicorn app.main:app --port 8001
```

### Permission Denied (Storage)
```bash
# Ensure write permissions
chmod -R 755 ./storage
```

### FFmpeg Not Found
```bash
# Install ffmpeg
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Or in Docker (already included)
```

### Database Locked
```bash
# Check for stuck processes
ps aux | grep uvicorn

# If needed, remove .db-wal and .db-shm files
rm storage/db/videos.db-*
```

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Type hints on all functions
- docstrings for complex logic
- Tests for new features
- Code formatted with black
- Passes ruff linting

## Support

See [USAGE.md](USAGE.md) for detailed API documentation.
See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details.

---

**Ready to get started?**

1. `cp .env.example .env`
2. `pip install -r requirements.txt`
3. `python -m uvicorn app.main:app --reload`
4. Visit http://localhost:8000/docs
