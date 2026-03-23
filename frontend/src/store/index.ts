import { create } from 'zustand'
import { Video, Tag, Category, DownloadStatus, VideoListResponse } from '@/types'
import { apiClient } from '@/api/client'

interface AppStore {
  // Videos
  videos: Video[]
  totalVideos: number
  currentPage: number
  videosLoading: boolean
  videosError: string | null

  // Tags
  tags: Tag[]
  tagsLoading: boolean

  // Categories
  categories: Category[]
  categoriesLoading: boolean

  // Search
  searchQuery: string
  searchResults: Video[]
  searchTotal: number
  searchLoading: boolean

  // Downloads
  activeDownloads: Map<string, DownloadStatus>

  // Actions
  fetchVideos: (page?: number, perPage?: number, filters?: any) => Promise<void>
  fetchTags: () => Promise<void>
  fetchCategories: () => Promise<void>
  fetchSearchResults: (query: string, filters?: any) => Promise<void>
  setSearchQuery: (query: string) => void
  addActiveDownload: (id: string, status: DownloadStatus) => void
  updateActiveDownload: (id: string, status: DownloadStatus) => void
  removeActiveDownload: (id: string) => void
  setVideosLoading: (loading: boolean) => void
  setVideosError: (error: string | null) => void
}

export const useAppStore = create<AppStore>((set) => ({
  // Initial state
  videos: [],
  totalVideos: 0,
  currentPage: 1,
  videosLoading: false,
  videosError: null,
  tags: [],
  tagsLoading: false,
  categories: [],
  categoriesLoading: false,
  searchQuery: '',
  searchResults: [],
  searchTotal: 0,
  searchLoading: false,
  activeDownloads: new Map(),

  // Actions
  fetchVideos: async (page = 1, perPage = 20, filters = {}) => {
    set({ videosLoading: true, videosError: null })
    try {
      const response: VideoListResponse = await apiClient.getVideos({
        page,
        per_page: perPage,
        ...filters,
      })
      set({
        videos: response.items,
        totalVideos: response.total,
        currentPage: page,
        videosLoading: false,
      })
    } catch (error: any) {
      set({
        videosError: error.message || 'Failed to fetch videos',
        videosLoading: false,
      })
    }
  },

  fetchTags: async () => {
    set({ tagsLoading: true })
    try {
      const tags = await apiClient.getTags()
      set({ tags, tagsLoading: false })
    } catch (error) {
      set({ tagsLoading: false })
    }
  },

  fetchCategories: async () => {
    set({ categoriesLoading: true })
    try {
      const categories = await apiClient.getCategories()
      set({ categories, categoriesLoading: false })
    } catch (error) {
      set({ categoriesLoading: false })
    }
  },

  fetchSearchResults: async (query: string, filters = {}) => {
    set({ searchLoading: true, searchQuery: query })
    try {
      const response: VideoListResponse = await apiClient.searchVideos(query, filters)
      set({
        searchResults: response.items,
        searchTotal: response.total,
        searchLoading: false,
      })
    } catch (error) {
      set({ searchLoading: false })
    }
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query })
  },

  addActiveDownload: (id: string, status: DownloadStatus) => {
    set((state) => {
      const newDownloads = new Map(state.activeDownloads)
      newDownloads.set(id, status)
      return { activeDownloads: newDownloads }
    })
  },

  updateActiveDownload: (id: string, status: DownloadStatus) => {
    set((state) => {
      const newDownloads = new Map(state.activeDownloads)
      newDownloads.set(id, status)
      return { activeDownloads: newDownloads }
    })
  },

  removeActiveDownload: (id: string) => {
    set((state) => {
      const newDownloads = new Map(state.activeDownloads)
      newDownloads.delete(id)
      return { activeDownloads: newDownloads }
    })
  },

  setVideosLoading: (loading: boolean) => {
    set({ videosLoading: loading })
  },

  setVideosError: (error: string | null) => {
    set({ videosError: error })
  },
}))
