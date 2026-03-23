import VideoCard from './VideoCard'
import { Video } from '@/types'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface VideoGridProps {
  videos: Video[]
  loading?: boolean
  error?: string | null
  currentPage?: number
  totalPages?: number
  onPageChange?: (page: number) => void
  onVideoDeleted?: () => void
}

export default function VideoGrid({
  videos,
  loading = false,
  error = null,
  currentPage = 1,
  totalPages = 1,
  onPageChange,
  onVideoDeleted,
}: VideoGridProps) {
  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 dark:text-red-400 font-semibold mb-2">
          Error loading videos
        </div>
        <p className="text-gray-600 dark:text-gray-400">{error}</p>
      </div>
    )
  }

  if (loading && videos.length === 0) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg overflow-hidden bg-white dark:bg-gray-800 shadow-sm animate-pulse"
          >
            <div className="aspect-video bg-gray-200 dark:bg-gray-700" />
            <div className="p-3 space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500 dark:text-gray-400 mb-4">
          <div className="inline-block p-4 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
            <svg
              className="w-12 h-12"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          No videos found
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          Start downloading videos to see them here
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {videos.map((video) => (
          <VideoCard key={video.id} video={video} onDelete={onVideoDeleted} />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange?.(currentPage - 1)}
            disabled={currentPage === 1}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <ChevronLeft size={20} />
          </button>

          <div className="flex gap-1">
            {Array.from({ length: totalPages }).map((_, i) => {
              const page = i + 1
              // Show first page, last page, current page, and neighbors
              if (
                page === 1 ||
                page === totalPages ||
                (page >= currentPage - 1 && page <= currentPage + 1)
              ) {
                return (
                  <button
                    key={page}
                    onClick={() => onPageChange?.(page)}
                    className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                      page === currentPage
                        ? 'bg-indigo-600 text-white'
                        : 'border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    {page}
                  </button>
                )
              }

              // Show ellipsis
              if (page === currentPage - 2 || page === currentPage + 2) {
                return (
                  <div key={page} className="w-10 h-10 flex items-center justify-center">
                    ...
                  </div>
                )
              }

              return null
            })}
          </div>

          <button
            onClick={() => onPageChange?.(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      )}
    </>
  )
}
