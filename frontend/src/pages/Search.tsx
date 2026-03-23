import { useSearch } from '@/hooks/useSearch'
import SearchBar from '@/components/search/SearchBar'
import VideoGrid from '@/components/video/VideoGrid'

export default function Search() {
  const { query, results, total, loading } = useSearch()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
          Search Videos
        </h1>
        <SearchBar />
      </div>

      {query && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Results for "{query}"
            </h2>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {total} result{total !== 1 ? 's' : ''}
            </span>
          </div>

          <VideoGrid videos={results} loading={loading} />

          {!loading && results.length === 0 && total === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-500 dark:text-gray-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No videos found
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Try searching with different keywords or check the Browse page
              </p>
            </div>
          )}
        </div>
      )}

      {!query && (
        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-500 mb-4">
            <svg
              className="w-16 h-16 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Start searching
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            Use the search bar above to find videos by title, tags, or uploader
          </p>
        </div>
      )}
    </div>
  )
}
