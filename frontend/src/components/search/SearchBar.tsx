import { Search, X } from 'lucide-react'
import { useSearch } from '@/hooks/useSearch'

export default function SearchBar() {
  const { query, total, setQuery, clear } = useSearch()

  return (
    <div className="w-full">
      <div className="relative flex items-center">
        <Search
          size={20}
          className="absolute left-3 text-gray-400 dark:text-gray-500 pointer-events-none"
        />
        <input
          type="text"
          placeholder="Search videos by title, tags, uploader..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-10 pr-10 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-900"
        />
        {query && (
          <button
            onClick={clear}
            className="absolute right-3 p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors"
          >
            <X size={20} className="text-gray-400 dark:text-gray-500" />
          </button>
        )}
      </div>
      {query && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Found {total} result{total !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
