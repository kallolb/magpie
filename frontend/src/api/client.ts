import axios, { AxiosInstance } from 'axios'
import {
  Video,
  VideoListResponse,
  DownloadRequest,
  DownloadStatus,
  Tag,
  Category,
  StorageStats,
  AppSettings,
  LoopMarker,
} from '@/types'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
})

// API key interceptor
api.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('api_key') || 'changeme'
  config.headers.Authorization = `Bearer ${apiKey}`
  return config
})

// API Functions
export const apiClient = {
  // Downloads
  submitDownload: (request: DownloadRequest): Promise<DownloadStatus> =>
    api.post('/downloads', request).then((res) => res.data),

  getDownloadStatus: (id: string): Promise<DownloadStatus> =>
    api.get(`/downloads/${id}`).then((res) => res.data),

  // Videos
  getVideos: (params?: {
    page?: number
    per_page?: number
    category?: string
    tags?: string[]
    platform?: string
    sort_by?: string
  }): Promise<VideoListResponse> =>
    api.get('/videos', { params }).then((res) => res.data),

  getVideo: (id: string): Promise<Video> =>
    api.get(`/videos/${id}`).then((res) => res.data),

  updateVideo: (
    id: string,
    data: Partial<Pick<Video, 'title' | 'description' | 'category' | 'tags'>>
  ): Promise<Video> =>
    api.put(`/videos/${id}`, data).then((res) => res.data),

  deleteVideo: (id: string): Promise<void> =>
    api.delete(`/videos/${id}`).then(() => undefined),

  // Search
  searchVideos: (
    query: string,
    filters?: { category?: string; tags?: string[] }
  ): Promise<VideoListResponse> =>
    api.post('/videos/search', { query, ...filters }).then((res) => res.data),

  // Stream URLs
  getVideoStreamUrl: (id: string): string => `/api/videos/${id}/stream`,

  getThumbnailUrl: (id: string): string => `/api/videos/${id}/thumbnail`,

  // Tags
  getTags: (): Promise<Tag[]> =>
    api.get('/tags').then((res) => res.data),

  createTag: (name: string): Promise<Tag> =>
    api.post('/tags', { name }).then((res) => res.data),

  deleteTag: (id: number): Promise<void> =>
    api.delete(`/tags/${id}`).then(() => undefined),

  // Categories
  getCategories: (): Promise<Category[]> =>
    api.get('/categories').then((res) => res.data),

  createCategory: (name: string, description?: string): Promise<Category> =>
    api.post('/categories', { name, description }).then((res) => res.data),

  deleteCategory: (name: string): Promise<void> =>
    api.delete(`/categories/${name}`).then(() => undefined),

  // Health & Settings
  getHealth: (): Promise<any> =>
    api.get('/health').then((res) => res.data),

  getSettings: (): Promise<AppSettings> =>
    api.get('/settings').then((res) => res.data),

  updateSettings: (settings: Partial<AppSettings>): Promise<AppSettings> =>
    api.put('/settings', settings).then((res) => res.data),

  // Storage Stats
  getStorageStats: (): Promise<StorageStats> =>
    api.get('/storage/stats').then((res) => res.data),

  // Loop Markers
  getLoopMarkers: (videoId: string): Promise<LoopMarker[]> =>
    api.get(`/videos/${videoId}/loops`).then((res) => res.data),

  createLoopMarker: (videoId: string, data: { label: string; start_secs: number; end_secs: number }): Promise<LoopMarker> =>
    api.post(`/videos/${videoId}/loops`, data).then((res) => res.data),

  deleteLoopMarker: (videoId: string, loopId: number): Promise<void> =>
    api.delete(`/videos/${videoId}/loops/${loopId}`).then(() => undefined),
}

export default api
