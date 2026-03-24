# Magpie API Usage Guide

## Setup

### Installation

1. Clone the repository and navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
pip install -e .
```

3. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

4. Update `.env` with your settings (especially `API_KEY`).

### Running the Application

#### Local Development
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the provided script:
```bash
chmod +x run.sh
./run.sh
```

#### Docker
```bash
docker build -t video-downloader .
docker run -p 8000:8000 -v $(pwd)/storage:/app/storage video-downloader
```

## API Endpoints

All endpoints (except `/api/health`) require the `X-API-Key` header.

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Downloads

#### Start a Download
```bash
curl -X POST http://localhost:8000/api/downloads \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "category": "music",
    "tags": ["tutorial", "important"],
    "quality": 1080
  }'
```

Response:
```json
{
  "id": "uuid-here",
  "status": "queued",
  "message": "Download queued successfully"
}
```

#### Get Download Status
```bash
curl http://localhost:8000/api/downloads/{video_id} \
  -H "X-API-Key: changeme"
```

#### Stream Progress (Server-Sent Events)
```bash
curl http://localhost:8000/api/downloads/{video_id}/progress \
  -H "X-API-Key: changeme"
```

#### Cancel Download
```bash
curl -X DELETE http://localhost:8000/api/downloads/{video_id} \
  -H "X-API-Key: changeme"
```

### Videos

#### List Videos
```bash
curl "http://localhost:8000/api/videos?page=1&per_page=20&category=music" \
  -H "X-API-Key: changeme"
```

#### Get Video Details
```bash
curl http://localhost:8000/api/videos/{video_id} \
  -H "X-API-Key: changeme"
```

#### Update Video
```bash
curl -X PUT http://localhost:8000/api/videos/{video_id} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "title": "New Title",
    "category": "tutorials",
    "tags": ["tag1", "tag2"]
  }'
```

#### Search Videos
```bash
curl -X POST http://localhost:8000/api/videos/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "query": "tutorial",
    "category": "tutorials",
    "tags": ["beginner"],
    "page": 1,
    "per_page": 20
  }'
```

#### Stream Video
```bash
curl http://localhost:8000/api/videos/{video_id}/stream \
  -H "X-API-Key: changeme" \
  -o video.mp4
```

#### Delete Video
```bash
curl -X DELETE http://localhost:8000/api/videos/{video_id} \
  -H "X-API-Key: changeme"
```

### Tags

#### List Tags
```bash
curl http://localhost:8000/api/tags \
  -H "X-API-Key: changeme"
```

#### Create Tag
```bash
curl -X POST http://localhost:8000/api/tags \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"name": "newtag"}'
```

#### Delete Tag
```bash
curl -X DELETE http://localhost:8000/api/tags/{tag_id} \
  -H "X-API-Key: changeme"
```

### Categories

#### List Categories
```bash
curl http://localhost:8000/api/categories \
  -H "X-API-Key: changeme"
```

#### Create Category
```bash
curl -X POST http://localhost:8000/api/categories \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "name": "mycategory",
    "description": "My custom category"
  }'
```

#### Delete Category
```bash
curl -X DELETE http://localhost:8000/api/categories/{category_name} \
  -H "X-API-Key: changeme"
```

### Webhook (Chat Bot Integration)

#### Ingest from External Source
```bash
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

### Loop Markers (A-B Repeat)

#### List Loop Markers for a Video
```bash
curl http://localhost:8000/api/videos/{video_id}/loops \
  -H "X-API-Key: changeme"
```

#### Create a Loop Marker
```bash
curl -X POST http://localhost:8000/api/videos/{video_id}/loops \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
    "label": "Chorus",
    "start_secs": 45.5,
    "end_secs": 78.2
  }'
```

#### Rename a Loop Marker
```bash
curl -X PUT http://localhost:8000/api/videos/{video_id}/loops/{loop_id} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"label": "Guitar Solo"}'
```

#### Delete a Loop Marker
```bash
curl -X DELETE http://localhost:8000/api/videos/{video_id}/loops/{loop_id} \
  -H "X-API-Key: changeme"
```

### Compilations

#### Create a Compilation
```bash
curl -X POST http://localhost:8000/api/compilations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"title": "Best Guitar Riffs", "category": "music"}'
```

#### List Compilations
```bash
curl http://localhost:8000/api/compilations \
  -H "X-API-Key: changeme"

# With search
curl "http://localhost:8000/api/compilations?q=guitar" \
  -H "X-API-Key: changeme"
```

#### Add a Clip
```bash
curl -X POST http://localhost:8000/api/compilations/{id}/clips \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"source_video_id": "vid-1", "start_secs": 45.0, "end_secs": 83.0, "label": "Solo"}'
```

#### Import a Loop Marker as Clip
```bash
curl -X POST http://localhost:8000/api/compilations/{id}/clips/from-loop/{loop_id} \
  -H "X-API-Key: changeme"
```

#### Reorder Clips
```bash
curl -X PUT http://localhost:8000/api/compilations/{id}/clips/reorder \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"clip_ids": [3, 1, 2]}'
```

#### Analyze Codec Compatibility
```bash
curl -X POST http://localhost:8000/api/compilations/{id}/analyze \
  -H "X-API-Key: changeme"
```

#### Render a Compilation
```bash
curl -X POST http://localhost:8000/api/compilations/{id}/render \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{"mode": "auto"}'
# mode: "copy" (fast), "reencode" (quality), or "auto" (recommended)
```

#### Stream Rendered Compilation
```bash
curl http://localhost:8000/api/compilations/{id}/stream \
  -H "X-API-Key: changeme" -o compilation.mp4
```

#### Check Video Deletion Impact
```bash
curl http://localhost:8000/api/videos/{video_id}/deletion-check \
  -H "X-API-Key: changeme"
```

### Analytics

#### Get All Analytics
```bash
curl http://localhost:8000/api/analytics \
  -H "X-API-Key: changeme"
```

Returns a JSON object with four sections:
- `storage` — total bytes, by category, by platform, largest videos, monthly growth
- `collection` — by status, by platform, by category, top uploaders, success rate
- `content` — duration/size/resolution distributions, top tags, avg duration by platform
- `activity` — daily downloads (30d), by day of week, recent vs prior week, loop marker stats

### Settings

#### Get Settings
```bash
curl http://localhost:8000/api/settings \
  -H "X-API-Key: changeme"
```

## Storage Structure

```
storage/
├── categories/
│   ├── music/
│   │   └── video1.mp4
│   ├── tutorials/
│   └── uncategorized/
├── thumbnails/
│   ├── uuid1.jpg
│   └── uuid2.jpg
└── db/
    └── videos.db
```

## Database Schema

- **videos**: Main video records
- **tags**: Available tags
- **video_tags**: Many-to-many relationship between videos and tags
- **categories**: Available categories
- **videos_fts**: Full-text search index (FTS5)
- **loop_markers**: Saved A-B loop regions per video
- **compilations**: User-created compilations (title, status, output path)
- **compilation_clips**: Clips referencing source videos with time ranges and ordering
- **download_log**: History of download attempts

## Features

### Auto-Categorization
Videos are automatically categorized based on title/description patterns:
- Tutorials: pattern-based detection
- Music: pattern-based detection
- Cooking: pattern-based detection
- Gaming: pattern-based detection
- Tech: pattern-based detection
- Sports: pattern-based detection
- News: pattern-based detection
- Entertainment: pattern-based detection
- Short-form: Instagram/TikTok or videos < 60 seconds

### Full-Text Search
Uses SQLite FTS5 with BM25 ranking. Search supports:
- Basic keywords
- Phrase searches
- Filtering by category and tags

### Video Streaming
Stream downloaded videos with:
- HTTP Range request support
- Proper Content-Type headers
- Resumable downloads

## Configuration

Edit `.env` to customize:

```env
# Storage location
STORAGE_ROOT=./storage

# Redis (for distributed task queues - optional)
REDIS_URL=redis://localhost:6379

# API security
API_KEY=your-secret-key

# Download preferences
DEFAULT_QUALITY=1080
DEFAULT_FORMAT=mp4
MAX_CONCURRENT_DOWNLOADS=3

# Server
API_HOST=0.0.0.0
API_PORT=8000
```

## Error Handling

All endpoints return appropriate HTTP status codes:
- 200: Success
- 201: Created
- 204: No Content (successful deletion)
- 400: Bad Request
- 401: Unauthorized (invalid API key)
- 404: Not Found
- 409: Conflict (duplicate)
- 500: Internal Server Error

## Performance Notes

- Database uses WAL (Write-Ahead Logging) for better concurrency
- FTS5 index is automatically maintained
- In-process async task queue by default (no Redis required)
- Tasks persist across restarts via database status tracking
