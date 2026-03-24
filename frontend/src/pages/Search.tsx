import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Film, Clock } from 'lucide-react'
import { useSearch } from '@/hooks/useSearch'
import SearchBar from '@/components/search/SearchBar'
import VideoGrid from '@/components/video/VideoGrid'
import { apiClient } from '@/api/client'
import { Compilation } from '@/types'

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.draft}`}>
      {status}
    </span>
  )
}

export default function Search() {
  const { query, results, total, loading } = useSearch()
  const navigate = useNavigate()
  const [scope, setScope] = useState<'all' | 'videos' | 'compilations'>('all')
  const [compilationResults, setCompilationResults] = useState<Compilation[]>([])
  const [compilationLoading, setCompilationLoading] = useState(false)

  useEffect(() => {
    if (!query?.trim() || scope === 'videos') {
      setCompilationResults([])
      return
    }
    setCompilationLoading(true)
    apiClient.searchCompilations(query)
      .then(setCompilationResults)
      .catch(() => setCompilationResults([]))
      .finally(() => setCompilationLoading(false))
  }, [query, scope])

  const showVideos = scope === 'all' || scope === 'videos'
  const showCompilations = scope === 'all' || scope === 'compilations'
  const totalResults = (showVideos ? total : 0) + (showCompilations ? compilationResults.length : 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Search
        </h1>
        <div className="flex items-center gap-3 mb-2">
          <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden text-sm">
            {(['all', 'videos', 'compilations'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setScope(s)}
                className={`px-3 py-1.5 font-medium transition-colors ${
                  scope === s
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {s === 'all' ? 'All' : s === 'videos' ? 'Videos' : 'Compilations'}
              </button>
            ))}
          </div>
        </div>
        <SearchBar />
      </div>

      {query && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Results for "{query}"
            </h2>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {totalResults} result{totalResults !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Video results */}
          {showVideos && results.length > 0 && (
            <div>
              {scope === 'all' && (
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Videos ({total})</h3>
              )}
              <VideoGrid videos={results} loading={loading} />
            </div>
          )}

          {/* Compilation results */}
          {showCompilations && compilationResults.length > 0 && (
            <div>
              {scope === 'all' && (
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Compilations ({compilationResults.length})</h3>
              )}
              <div className="space-y-2">
                {compilationResults.map((comp) => (
                  <div
                    key={comp.id}
                    onClick={() => navigate(`/compilations/${comp.id}`)}
                    className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-3 hover:border-indigo-300 dark:hover:border-indigo-700 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Film size={18} className="text-indigo-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-white truncate">{comp.title}</span>
                          <StatusBadge status={comp.status} />
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                          <span>{comp.clip_count} clips</span>
                          {comp.estimated_duration_secs > 0 && (
                            <span className="flex items-center gap-1"><Clock size={10} /> {formatTime(comp.estimated_duration_secs)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!loading && !compilationLoading && totalResults === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-500 dark:text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No results found</h3>
              <p className="text-gray-600 dark:text-gray-400">Try different keywords or change the search scope</p>
            </div>
          )}
        </div>
      )}

      {!query && (
        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-500 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Start searching</h3>
          <p className="text-gray-600 dark:text-gray-400">Search across videos and compilations by title, tags, or uploader</p>
        </div>
      )}
    </div>
  )
}
