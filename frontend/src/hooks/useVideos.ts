import { useEffect, useCallback } from 'react'
import { useAppStore } from '@/store'

interface UseVideosOptions {
  page?: number
  perPage?: number
  category?: string
  tags?: string[]
  platform?: string
  sortBy?: string
}

export const useVideos = (options: UseVideosOptions = {}) => {
  const {
    videos,
    totalVideos,
    currentPage,
    videosLoading,
    videosError,
    fetchVideos,
  } = useAppStore()

  useEffect(() => {
    const page = options.page || 1
    const perPage = options.perPage || 20
    fetchVideos(page, perPage, {
      category: options.category,
      tags: options.tags,
      platform: options.platform,
      sort_by: options.sortBy,
    })
  }, [
    options.page,
    options.perPage,
    options.category,
    options.tags,
    options.platform,
    options.sortBy,
    fetchVideos,
  ])

  const goToPage = useCallback(
    (page: number) => {
      const perPage = options.perPage || 20
      fetchVideos(page, perPage, {
        category: options.category,
        tags: options.tags,
        platform: options.platform,
        sort_by: options.sortBy,
      })
    },
    [fetchVideos, options]
  )

  const totalPages = Math.ceil(totalVideos / (options.perPage || 20))

  return {
    videos,
    totalVideos,
    currentPage,
    totalPages,
    loading: videosLoading,
    error: videosError,
    goToPage,
    refetch: () => {
      const page = options.page || 1
      const perPage = options.perPage || 20
      fetchVideos(page, perPage, {
        category: options.category,
        tags: options.tags,
        platform: options.platform,
        sort_by: options.sortBy,
      })
    },
  }
}
