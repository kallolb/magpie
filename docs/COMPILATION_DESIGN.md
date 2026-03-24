# Compilation Feature — Design Document

## 1. Overview

The compilation feature allows users to create new videos by combining clips from existing videos in their library. This is useful for creating highlight reels, study materials, or "best of" collections from similar videos — for example, collecting the best guitar riffs from multiple lesson videos into a single practice compilation.

### User Stories

- As a music learner, I want to extract the best sections from multiple lesson videos and combine them into a single practice video
- As a user, I want to reuse my saved loop markers as clips in a compilation
- As a user, I want to preview individual clips before committing to a full render
- As a user, I want to know upfront whether my clips are compatible for fast rendering or need re-encoding
- As a user, I want to search across both regular videos and compilations

### Non-Goals

- Video editing (trimming, transitions, effects, overlays)
- Audio mixing or normalization across clips
- Real-time collaborative editing

---

## 2. Data Model

### New Tables

```sql
CREATE TABLE IF NOT EXISTS compilations (
    id TEXT PRIMARY KEY,                          -- UUID
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'compilations',
    status TEXT NOT NULL DEFAULT 'draft',          -- draft, analyzing, rendering, completed, failed
    render_mode TEXT,                              -- 'copy' (stream copy) or 'reencode'
    output_path TEXT,                              -- relative to STORAGE_ROOT, set after render
    output_size_bytes INTEGER,
    duration_secs REAL,
    thumbnail_path TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS compilation_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compilation_id TEXT NOT NULL REFERENCES compilations(id) ON DELETE CASCADE,
    source_video_id TEXT NOT NULL REFERENCES videos(id),
    position INTEGER NOT NULL,                    -- 1-based ordering
    start_secs REAL NOT NULL,
    end_secs REAL NOT NULL,
    label TEXT,                                   -- optional note, e.g. "great solo"
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_compilation_clips_compilation_id ON compilation_clips(compilation_id);
CREATE INDEX IF NOT EXISTS idx_compilation_clips_source_video ON compilation_clips(source_video_id);
CREATE INDEX IF NOT EXISTS idx_compilations_status ON compilations(status);
CREATE INDEX IF NOT EXISTS idx_compilations_category ON compilations(category);
```

### Key Design Decisions

- **Separate from videos table** — Compilations have a different lifecycle (draft → render → completed) and don't have fields like `platform`, `uploader`, or `source_url` that apply to downloaded videos
- **Cascade delete on clips** — Deleting a compilation removes all its clips
- **No cascade on source video delete** — If a source video is deleted, its clips remain but become unrenderable. The render pipeline will detect and report this. Users can remove broken clips manually
- **`render_mode` column** — Records whether the compilation was rendered via stream copy or re-encoding, useful for understanding render times
- **`position` column** — Integer for explicit ordering. Reordering updates position values for affected clips

### Storage Layout

```
{STORAGE_ROOT}/
├── compilations/                    -- rendered output files
│   ├── {compilation_id}.mp4
│   └── ...
├── compilations_tmp/                -- temporary clip files during render (cleaned up after)
│   └── {compilation_id}/
│       ├── clip_001.mp4
│       ├── clip_002.mp4
│       └── concat.txt
```

---

## 3. Backend API Design

### Compilation CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/compilations` | Create compilation (title, description, category) |
| `GET` | `/api/compilations` | List compilations (paginated, filterable by status/category) |
| `GET` | `/api/compilations/{id}` | Get compilation with all clips and source video metadata |
| `PUT` | `/api/compilations/{id}` | Update title, description, or category |
| `DELETE` | `/api/compilations/{id}` | Delete compilation, output file, and all clips |

### Clip Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/compilations/{id}/clips` | Add a clip (source_video_id, start_secs, end_secs, label) |
| `PUT` | `/api/compilations/{id}/clips/{clip_id}` | Update clip (start_secs, end_secs, label) |
| `DELETE` | `/api/compilations/{id}/clips/{clip_id}` | Remove a clip (auto-reorders remaining) |
| `PUT` | `/api/compilations/{id}/clips/reorder` | Reorder clips (body: `{clip_ids: [3, 1, 2]}`) |
| `POST` | `/api/compilations/{id}/clips/from-loop/{loop_id}` | Import a loop marker as a clip |

### Render Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/compilations/{id}/analyze` | Analyze clips for codec compatibility, return recommendation |
| `POST` | `/api/compilations/{id}/render` | Start render (body: `{mode: "copy" \| "reencode" \| "auto"}`) |
| `GET` | `/api/compilations/{id}/render/progress` | SSE stream for render progress |
| `GET` | `/api/compilations/{id}/stream` | Stream the rendered output file |

### Search Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/search` | Unified search (body: `{query, scope: "videos" \| "compilations" \| "all"}`) |

### Response Models

#### CompilationResponse
```json
{
  "id": "comp-uuid",
  "title": "Best Guitar Riffs",
  "description": "Collection of my favorite solos",
  "category": "compilations",
  "status": "draft",
  "render_mode": null,
  "output_path": null,
  "output_size_bytes": null,
  "duration_secs": null,
  "thumbnail_path": null,
  "clip_count": 3,
  "estimated_duration_secs": 125.5,
  "created_at": "2026-03-23T...",
  "updated_at": "2026-03-23T...",
  "clips": [
    {
      "id": 1,
      "source_video_id": "vid-1",
      "source_video_title": "Guitar Lesson 3",
      "source_video_thumbnail": "/api/thumbnails/vid-1.jpg",
      "position": 1,
      "start_secs": 45.0,
      "end_secs": 83.0,
      "label": "Blues solo",
      "duration_secs": 38.0
    }
  ]
}
```

#### AnalyzeResponse
```json
{
  "compatible": false,
  "recommendation": "reencode",
  "reason": "Clips use different resolutions: 1080p (2 clips), 720p (1 clip)",
  "clips": [
    {
      "clip_id": 1,
      "source_video_id": "vid-1",
      "codec": "h264",
      "resolution": "1920x1080",
      "audio_codec": "aac",
      "compatible": true
    },
    {
      "clip_id": 3,
      "source_video_id": "vid-5",
      "codec": "h264",
      "resolution": "1280x720",
      "audio_codec": "aac",
      "compatible": false
    }
  ],
  "options": [
    {
      "mode": "copy",
      "label": "Fast (stream copy)",
      "description": "Instant, but may have glitches at clip boundaries due to resolution mismatch",
      "estimated_time": "< 5 seconds",
      "available": true
    },
    {
      "mode": "reencode",
      "label": "Best quality (re-encode)",
      "description": "Normalizes all clips to 1080p H.264/AAC. Slower but guaranteed smooth playback",
      "estimated_time": "~2 minutes",
      "available": true
    }
  ]
}
```

---

## 4. Render Pipeline — Technical Detail

### Codec Analysis

Before rendering, the analyze endpoint probes each source video using ffprobe:

```bash
ffprobe -v quiet -print_format json -show_streams source.mp4
```

This extracts: video codec (h264, vp9, etc.), resolution, frame rate, audio codec, sample rate. Clips are "compatible" for stream copy if all have the same video codec, resolution, and audio codec.

### Stream Copy Path (Fast)

When all clips are compatible:

```bash
# Step 1: Cut each clip (stream copy — no re-encoding)
ffmpeg -i source1.mp4 -ss 45.0 -to 83.0 -c copy -avoid_negative_ts make_zero clip_001.mp4
ffmpeg -i source2.mp4 -ss 12.0 -to 34.0 -c copy -avoid_negative_ts make_zero clip_002.mp4

# Step 2: Concatenate
# concat.txt:
#   file 'clip_001.mp4'
#   file 'clip_002.mp4'
ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
```

**Characteristics:** Near-instant, preserves original quality, no CPU overhead. May have minor seeking artifacts at clip boundaries (keyframe alignment).

### Re-encode Path (Best Quality)

When clips have different codecs/resolutions, or user chooses quality:

```bash
# Single ffmpeg command with filter_complex for concatenation
ffmpeg \
  -i source1.mp4 -i source2.mp4 \
  -filter_complex "
    [0:v]trim=start=45:end=83,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v0];
    [0:a]atrim=start=45:end=83,asetpts=PTS-STARTPTS[a0];
    [1:v]trim=start=12:end=34,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v1];
    [1:a]atrim=start=12:end=34,asetpts=PTS-STARTPTS[a1];
    [v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]
  " \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 128k \
  output.mp4
```

**Characteristics:** Slower (depends on total clip duration and CPU), normalizes everything to consistent codec/resolution, smooth playback guaranteed.

For many clips (>5-6), the filter_complex approach may hit ffmpeg argument limits. In that case, use the two-step approach: re-encode each clip individually to a common format, then concat with stream copy.

### Progress Tracking

ffmpeg outputs progress to stderr. We can parse it by running ffmpeg with `-progress pipe:1` which outputs key=value pairs:

```
out_time_us=12345678
speed=2.5x
progress=continue
```

The background task reads these, computes percentage based on estimated total duration, and writes to the compilation's status in the database. The SSE endpoint polls and streams updates — same pattern as the download progress system.

### Thumbnail Generation

After successful render, generate a thumbnail from the first second of the output:

```bash
ffmpeg -i output.mp4 -ss 00:00:01 -vframes 1 -vf scale=640:-1 thumbnail.jpg
```

---

## 5. Frontend Design

### Navigation

Add "Compilations" to the sidebar between "Analytics" and "Settings" using the `Scissors` icon from Lucide.

Route: `/compilations` — list page
Route: `/compilations/{id}` — editor
Route: `/compilations/{id}/play` — playback (reuses VideoPlayer)

### Compilations List Page (`/compilations`)

```
┌─────────────────────────────────────────────────────────────────┐
│  Compilations                              [+ New Compilation]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🎬 Best Guitar Riffs                                   │    │
│  │  ┌─────┐                                                │    │
│  │  │thumb│  3 clips · 2:05 · Draft                        │    │
│  │  └─────┘  Created Mar 23, 2026                          │    │
│  │           [Edit]  [Delete]                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🎬 Cooking Highlights                                  │    │
│  │  ┌─────┐                                                │    │
│  │  │thumb│  5 clips · 4:30 · Completed ✓                  │    │
│  │  └─────┘  Rendered Mar 22, 2026 · 89 MB                 │    │
│  │           [Play]  [Edit]  [Delete]                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Status badges:
- **Draft** — gray badge, shows "Edit" button
- **Analyzing** — blue badge with spinner
- **Rendering** — blue badge with progress percentage
- **Completed** — green badge with checkmark, shows "Play" button
- **Failed** — red badge, shows error message on hover

### Compilation Editor (`/compilations/{id}`)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back                                                                │
│                                                                         │
│  ┌─────────────────────────────────────┬───────────────────────────────┐│
│  │  Title: Best Guitar Riffs    [✏️]   │                               ││
│  │  Category: music             [✏️]   │                               ││
│  │  3 clips · ~2:05 estimated          │                               ││
│  │                                     │      Clip Preview             ││
│  │  ┌─────────────────────────────┐    │                               ││
│  │  │ ⋮  1. Blues solo            │    │   ┌───────────────────────┐   ││
│  │  │     Guitar Lesson 3         │    │   │                       │   ││
│  │  │     0:45 → 1:23 (38s)      │    │   │    Video Player       │   ││
│  │  │     [Preview] [✏️] [✕]     │ ◄──│   │    (source video      │   ││
│  │  └─────────────────────────────┘    │   │     seeked to clip)   │   ││
│  │                                     │   │                       │   ││
│  │  ┌─────────────────────────────┐    │   └───────────────────────┘   ││
│  │  │ ⋮  2. Intro riff           │    │                               ││
│  │  │     Rock Techniques         │    │   Playing: clip 1 of 3       ││
│  │  │     0:12 → 0:34 (22s)      │    │   0:45 ━━━━━━━━━━━━━ 1:23   ││
│  │  │     [Preview] [✏️] [✕]     │    │                               ││
│  │  └─────────────────────────────┘    │                               ││
│  │                                     │                               ││
│  │  ┌─────────────────────────────┐    │                               ││
│  │  │ ⋮  3. Pentatonic run       │    │                               ││
│  │  │     Scale Exercises          │    │                               ││
│  │  │     2:10 → 3:15 (65s)      │    │                               ││
│  │  │     [Preview] [✏️] [✕]     │    │                               ││
│  │  └─────────────────────────────┘    │                               ││
│  │                                     │                               ││
│  │  [+ Add Clip]  [+ From Loop]        │                               ││
│  │                                     │                               ││
│  │  ──────────────────────────────     │                               ││
│  │  [🔍 Analyze Compatibility]         │                               ││
│  │  [▶ Render Compilation]             │                               ││
│  └─────────────────────────────────────┴───────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

#### Left Panel — Clip List
- Draggable clip cards (Phase 3: drag-and-drop; Phase 1: up/down arrow buttons)
- Each card shows: position, label, source video title, time range, duration
- **Preview** button loads the source video in the right panel, seeked to clip range
- **Edit** (pencil) opens inline editing for label and start/end times
- **Delete** (✕) removes the clip with confirmation
- **Add Clip** button opens a modal to browse/search videos and set A/B markers
- **From Loop** button shows existing loop markers to import

#### Right Panel — Preview
- Shows the source video player when a clip is selected for preview
- Uses the existing loop playback mechanism (timeupdate listener) to loop within the clip's time range
- Shows which clip is being previewed and its time range

#### Bottom Actions
- **Analyze Compatibility** — calls the analyze endpoint, shows a result card:
  ```
  ┌────────────────────────────────────────────────────┐
  │  ⚠️ Mixed resolutions detected                     │
  │  2 clips at 1080p, 1 clip at 720p                  │
  │                                                    │
  │  ○ Fast (stream copy)                              │
  │    Instant render, may have resolution jumps        │
  │                                                    │
  │  ● Best quality (re-encode)           ← recommended │
  │    ~2 min render, smooth 1080p output               │
  │                                                    │
  │  [Render with selected option]                      │
  └────────────────────────────────────────────────────┘
  ```
  If all clips are compatible:
  ```
  ┌────────────────────────────────────────────────────┐
  │  ✅ All clips compatible (H.264 1080p AAC)         │
  │                                                    │
  │  ● Fast (stream copy)                ← recommended │
  │    Instant render, original quality                 │
  │                                                    │
  │  ○ Best quality (re-encode)                        │
  │    ~2 min render, normalized output                 │
  │                                                    │
  │  [Render with selected option]                      │
  └────────────────────────────────────────────────────┘
  ```
- **Render** — starts the render, shows progress bar inline, disables editing

#### Add Clip Modal

```
┌────────────────────────────────────────────────────────────┐
│  Add Clip                                            [✕]   │
│                                                            │
│  Search: [_________________________] 🔍                     │
│                                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │  ┌─────┐  Guitar Lesson 3                          │    │
│  │  │thumb│  tutorials · 30:00 · 1080p                │    │
│  │  └─────┘  [Select]                                 │    │
│  ├────────────────────────────────────────────────────┤    │
│  │  ┌─────┐  Rock Techniques                          │    │
│  │  │thumb│  music · 15:20 · 720p                     │    │
│  │  └─────┘  [Select]                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ── After selecting a video: ──                            │
│                                                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │            [Video Player]                          │    │
│  │     [Set A: 0:45]    [Set B: 1:23]                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  Label: [Blues solo________________]                        │
│                                                            │
│  [Cancel]                                [Add to Compilation]│
└────────────────────────────────────────────────────────────┘
```

Reuses the same Set A / Set B mechanism from the loop markers feature. The video player in the modal shows the source video with A/B controls.

#### From Loop Marker Modal

```
┌────────────────────────────────────────────────────────────┐
│  Import from Loop Markers                            [✕]   │
│                                                            │
│  ☐  Guitar Lesson 3                                        │
│     ☐ Blues solo (0:45 → 1:23)                             │
│     ☐ Verse progression (2:00 → 2:45)                     │
│                                                            │
│  ☐  Scale Exercises                                        │
│     ☐ Pentatonic run (2:10 → 3:15)                        │
│     ☐ Chromatic warmup (0:00 → 0:30)                      │
│                                                            │
│  [Cancel]                          [Import 0 selected]      │
└────────────────────────────────────────────────────────────┘
```

Groups loop markers by video. Checkboxes for multi-select. Selected loops are added as clips at the end of the list.

### Search Integration

The existing search page gets a scope selector:

```
[Videos ▾]  [____search query____] 🔍

↓ dropdown:
  ● All
  ○ Videos only
  ○ Compilations only
```

Compilation search results show differently from video results — they display clip count, duration, and status instead of platform/uploader.

---

## 6. Source Video Deletion Handling

When a user tries to delete a video that is referenced by compilation clips:

1. Check if any `compilation_clips` reference this `source_video_id`
2. If yes, show a warning: "This video is used in N compilation(s): [list]. Deleting it will make those clips unrenderable."
3. User can proceed (clips remain but are flagged) or cancel
4. If the video is deleted, the render pipeline will detect missing source files and report which clips are broken
5. The compilation editor shows broken clips with a warning icon and suggests removal

---

## 7. Implementation Phases

> **Status: All three phases are complete.**

### Phase 1 — Backend CRUD + Basic Editor (DONE)

**Backend:**
- `compilations` and `compilation_clips` tables in `database.py`
- Pydantic models: `CompilationCreate`, `CompilationUpdate`, `CompilationResponse`, `ClipCreate`, `ClipUpdate`, `ClipResponse`
- Router: `compilations.py` with all CRUD and clip management endpoints
- Clip reordering via up/down (swap positions)
- Register router in `main.py`

**Frontend:**
- Compilations list page with create/delete
- Compilation editor with clip list (add, remove, rename, reorder with arrows)
- Add Clip modal with video search and A/B marker selection
- Import from Loop Markers modal
- Sidebar navigation entry

**Tests:**
- CRUD tests for compilations and clips
- Reorder tests
- Loop marker import test
- Cascade delete test

### Phase 2 — Render Pipeline + Playback (DONE)

**Backend:**
- Analyze endpoint using ffprobe
- Render background task (stream copy + re-encode paths)
- Progress tracking via SSE (same pattern as download progress)
- Thumbnail generation for completed compilations
- Stream endpoint for playback

**Frontend:**
- Analyze compatibility UI with option selection
- Render button with inline progress bar
- Play button for completed compilations (reuses VideoPlayer)
- Status badges on list page
- Error display for failed renders

**Tests:**
- Analyze endpoint tests (mock ffprobe)
- Render task tests (mock ffmpeg)
- SSE progress tests

### Phase 3 — Polish (DONE)

**Frontend:**
- Drag-and-drop clip reordering (react-dnd or @dnd-kit)
- Clip preview in right panel (source video seeked to clip range)
- Search scope selector (videos / compilations / all)
- Source video deletion warning when referenced by compilations
- Timeline visualization showing clip boundaries
- Compilation thumbnail in list view

**Backend:**
- Unified search endpoint with scope parameter
- Source video deletion check endpoint or warning in delete response

---

## 8. Files That Will Change

| Phase | Backend Files | Frontend Files |
|-------|--------------|----------------|
| Phase 1 | `database.py`, `models/compilation.py`, `routers/compilations.py`, `main.py`, `tests/test_api_compilations.py` | `types/index.ts`, `api/client.ts`, `App.tsx`, `Sidebar.tsx`, `pages/Compilations.tsx`, `pages/CompilationEditor.tsx` |
| Phase 2 | `services/renderer.py`, `routers/compilations.py` (analyze, render, stream endpoints) | `CompilationEditor.tsx` (analyze UI, render progress, play button) |
| Phase 3 | `routers/compilations.py` (search), `routers/videos.py` (deletion warning) | `CompilationEditor.tsx` (drag-drop, preview), `pages/Search.tsx` (scope) |

---

## 9. Dependencies

- **ffmpeg** — already installed in the backend Docker image
- **ffprobe** — bundled with ffmpeg, used for codec analysis
- **No new Python packages** — uses `asyncio.create_subprocess_exec` for ffmpeg/ffprobe (same pattern as thumbnail generation)
- **Frontend Phase 3** — may add `@dnd-kit/core` and `@dnd-kit/sortable` for drag-and-drop (~15KB gzipped)
