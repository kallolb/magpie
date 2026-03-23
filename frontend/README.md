# Magpie - Frontend

A modern React + TypeScript web interface for a self-hosted video downloader application.

## Features

- **Download Management**: Download videos from YouTube and Instagram with quality selection
- **Video Organization**: Organize videos into categories and tag them for easy discovery
- **Smart Search**: Full-text search across video titles, tags, and metadata
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Progress**: Monitor active downloads with live progress updates
- **Storage Management**: Track storage usage and manage disk space
- **Settings Panel**: Configure API keys, manage categories, and control tags

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **React Router v6** - Client-side routing
- **Zustand** - State management
- **Axios** - HTTP client
- **Lucide React** - Icons

## Installation

### Prerequisites

- Node.js 16+
- npm or yarn
- Backend running at `http://localhost:8000`

### Setup

```bash
cd frontend
npm install
```

### Development

Start the development server with hot module reloading:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` with automatic API proxy to `http://localhost:8000`.

### Build

Create an optimized production build:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/           # API client and endpoints
│   ├── components/    # Reusable React components
│   │   ├── layout/    # Layout components (Sidebar, Header)
│   │   ├── video/     # Video-related components
│   │   ├── search/    # Search functionality
│   │   ├── tags/      # Tag management
│   │   └── settings/  # Settings components
│   ├── hooks/         # Custom React hooks
│   ├── pages/         # Page components
│   ├── store/         # Zustand state management
│   ├── types/         # TypeScript type definitions
│   ├── utils/         # Utility functions
│   ├── App.tsx        # Main app component with routing
│   └── main.tsx       # Entry point
├── public/            # Static assets
├── index.html         # HTML template
├── package.json       # Dependencies and scripts
├── tailwind.config.ts # Tailwind CSS configuration
├── tsconfig.json      # TypeScript configuration
├── vite.config.ts     # Vite configuration
└── Dockerfile         # Container image definition
```

## Configuration

### API Key

The frontend uses a Bearer token for API authentication. Set it in the Settings page or in localStorage:

```javascript
localStorage.setItem('api_key', 'your-api-key')
```

Default value: `changeme`

### Environment Variables

Create a `.env.local` file (optional):

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Docker

Build a Docker image:

```bash
docker build -t magpie-frontend .
```

Run the container:

```bash
docker run -p 80:80 magpie-frontend
```

The application will be served at `http://localhost` and automatically proxy API requests to `http://backend:8000`.

## Available Pages

- **Dashboard** (`/`) - Overview with recent downloads and quick actions
- **Browse** (`/browse`) - Browse all videos with advanced filtering
- **Download** (`/download`) - Download videos with full form
- **Video Detail** (`/video/:id`) - View and edit individual videos
- **Search** (`/search`) - Full-text search functionality
- **Settings** (`/settings`) - Configure API key, categories, and tags

## Features Details

### Download Form
- URL validation with platform detection (YouTube/Instagram)
- Quality selection (360p to 1080p, best available)
- Category assignment
- Tag management with autocomplete
- Live progress tracking via Server-Sent Events

### Video Management
- Inline editing of title, category, and tags
- Delete with confirmation
- Copy source URL and file path to clipboard
- View original platform URL
- Thumbnail and metadata display

### Search & Filter
- Debounced full-text search
- Filter by category, platform, and tags
- Multiple sort options (date, title, duration, size)
- Real-time result count

### Storage Configuration
- Visual storage usage bar
- Free space indicator
- Video count tracking
- High usage warnings

## API Endpoints

The frontend communicates with the backend through these endpoints:

- `GET /api/health` - Health check
- `GET /api/videos` - List videos with pagination
- `GET /api/videos/:id` - Get video details
- `PUT /api/videos/:id` - Update video metadata
- `DELETE /api/videos/:id` - Delete video
- `GET /api/search` - Search videos
- `POST /api/downloads` - Submit new download
- `GET /api/downloads/:id` - Get download status
- `GET /api/downloads/:id/progress` - SSE stream for download progress
- `GET /api/videos/:id/stream` - Stream video file
- `GET /api/videos/:id/thumbnail` - Get thumbnail
- `GET /api/tags` - List all tags
- `POST /api/tags` - Create tag
- `DELETE /api/tags/:id` - Delete tag
- `GET /api/categories` - List categories
- `POST /api/categories` - Create category
- `DELETE /api/categories/:name` - Delete category
- `GET /api/storage/stats` - Storage statistics
- `GET /api/settings` - Get app settings

## Performance Optimizations

- Code splitting with React Router lazy loading
- Image optimization for thumbnails
- Debounced search (300ms)
- Pagination for large video lists
- Responsive grid layout with CSS Grid

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development Guidelines

### Component Structure

Components are organized by feature:
- **Layout** - App structure (header, sidebar)
- **Video** - Video display and interaction
- **Search** - Search interface
- **Tags** - Tag management
- **Settings** - Configuration panels

### State Management

Use Zustand store for global state:
- Video list and pagination
- Tags and categories
- Active downloads
- Search results

### Styling

- Tailwind CSS for all styling
- Dark mode support with `dark:` prefix
- Consistent color scheme (indigo primary, slate neutrals)
- Responsive breakpoints: sm, md, lg, xl

## Troubleshooting

### API Connection Errors

If you see "Offline" in the header:
1. Verify backend is running on `http://localhost:8000`
2. Check API key in Settings
3. Check browser console for detailed errors

### Video Playback Issues

1. Verify backend stream endpoint is accessible
2. Check video file exists on disk
3. Verify browser supports H.264 video codec

### CORS Errors

Should be automatically proxied by Vite dev server. In production, ensure nginx config includes proper CORS headers.

## Contributing

1. Follow TypeScript strict mode
2. Use functional components with hooks
3. Implement proper error handling
4. Add loading states for async operations
5. Test responsive design on multiple screen sizes

## License

Same as main project
