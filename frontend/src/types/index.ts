export interface Video {
  id: string
  title: string
  description?: string
  source_url: string
  uploader?: string
  platform: string
  platform_id?: string
  duration_secs?: number
  resolution?: string
  file_size_bytes?: number
  file_path?: string
  thumbnail_path?: string
  category: string
  status: string
  error_message?: string
  progress: number
  created_at: string
  updated_at: string
  upload_date?: string
  tags: string[]
}

export interface VideoListResponse {
  items: Video[]
  total: number
  page: number
  per_page: number
}

export interface DownloadRequest {
  url: string
  category?: string
  tags?: string[]
  quality?: number
}

export interface DownloadStatus {
  id: string
  status: 'pending' | 'downloading' | 'processing' | 'completed' | 'failed' | 'duplicate'
  progress: number
  error_message?: string
  video?: Video
}

export interface Tag {
  id: number
  name: string
  video_count: number
}

export interface Category {
  name: string
  description?: string
  video_count: number
}

export interface SearchResult {
  items: Video[]
  total: number
  query: string
}

export interface StorageStats {
  total_bytes: number
  used_bytes: number
  free_bytes: number
  video_count: number
}

export interface AppSettings {
  api_key: string
  storage_path: string
  max_concurrent_downloads: number
}

export interface CompilationClip {
  id: number
  compilation_id: string
  source_video_id: string
  source_video_title?: string
  source_video_thumbnail?: string
  position: number
  start_secs: number
  end_secs: number
  duration_secs: number
  label?: string
  created_at: string
}

export interface Compilation {
  id: string
  title: string
  description?: string
  category: string
  status: string
  render_mode?: string
  output_path?: string
  output_size_bytes?: number
  duration_secs?: number
  thumbnail_path?: string
  error_message?: string
  clip_count: number
  estimated_duration_secs: number
  created_at: string
  updated_at: string
  clips: CompilationClip[]
}

export interface LoopMarker {
  id: number
  video_id: string
  label: string
  start_secs: number
  end_secs: number
  created_at: string
}
