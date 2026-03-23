import { useState, useEffect } from 'react'
import { Filter } from 'lucide-react'
import { useVideos } from '@/hooks/useVideos'
import { useAppStore } from '@/store'
import VideoGrid from '@/components/video/VideoGrid'

export default function Browse() {
  const { categories, fetchCategories } = useAppStore()
  const [showFilters, setShowFilters] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedPlatform, setSelectedPlatform] = useState<string>('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [sortBy, setSortBy] = useState('date')
  const [page, setPage] = useState(1)

  const { videos, totalVideos, totalPages, loading, error, goToPage, refetch } = useVideos({
    page,
    perPage: 20,
    category: selectedCategory,
    platform: selectedPlatform,
    tags: selectedTags.length > 0 ? selectedTags : undefined,
    sortBy,
  })

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category)
    setPage(1)
  }

  const handlePlatformChange = (platform: string) => {
    setSelectedPlatform(platform)
    setPage(1)
  }

  const handleSortChange = (sort: string) => {
    setSortBy(sort)
    setPage(1)
  }

  return (
    <div className="space-y-6">
      {/* Filter Bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Browse Videos
        </h1>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <Filter size={18} />
          <span>Filters</span>
        </button>
      </div>

      {/* Active Filters Display */}
      {(selectedCategory || selectedPlatform || selectedTags.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {selectedCategory && (
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-full text-sm">
              {selectedCategory}
              <button
                onClick={() => handleCategoryChange('')}
                className="ml-1 hover:opacity-75"
              >
                ✕
              </button>
            </div>
          )}
          {selectedPlatform && (
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-sm">
              {selectedPlatform}
              <button
                onClick={() => handlePlatformChange('')}
                className="ml-1 hover:opacity-75"
              >
                ✕
              </button>
            </div>
          )}
          {selectedTags.map((tag) => (
            <div
              key={tag}
              className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-sm"
            >
              {tag}
              <button
                onClick={() => setSelectedTags(selectedTags.filter((t) => t !== tag))}
                className="ml-1 hover:opacity-75"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.video_count})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Platform
            </label>
            <select
              value={selectedPlatform}
              onChange={(e) => handlePlatformChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Platforms</option>
              <option value="youtube">YouTube</option>
              <option value="instagram">Instagram</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="date">Newest First</option>
              <option value="date_asc">Oldest First</option>
              <option value="title">Title (A-Z)</option>
              <option value="duration">Duration</option>
              <option value="size">File Size</option>
            </select>
          </div>
        </div>
      )}

      {/* Videos Grid */}
      <VideoGrid
        videos={videos}
        loading={loading}
        error={error}
        currentPage={page}
        totalPages={totalPages}
        onPageChange={goToPage}
        onVideoDeleted={() => { refetch(); fetchCategories(); }}
      />

      {/* Results Count */}
      {!loading && (
        <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
          Showing {videos.length} of {totalVideos} videos
        </p>
      )}
    </div>
  )
}
