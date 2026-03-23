import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Menu, Circle, AlertCircle } from 'lucide-react'
import { useSearch } from '@/hooks/useSearch'
import { apiClient } from '@/api/client'

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { query, setQuery } = useSearch()
  const navigate = useNavigate()
  const location = useLocation()
  const [connected, setConnected] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await apiClient.getHealth()
        setConnected(true)
      } catch {
        setConnected(false)
      } finally {
        setChecking(false)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          {/* Menu button for mobile */}
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <Menu size={24} className="text-gray-600 dark:text-gray-400" />
          </button>

          {/* Search bar */}
          <div className="flex-1 max-w-2xl mx-auto">
            <input
              type="text"
              placeholder="Search videos..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                if (e.target.value.trim() && location.pathname !== '/search') {
                  navigate('/search')
                }
              }}
              className="w-full px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* API Status */}
          <div className="flex items-center gap-2">
            {checking ? (
              <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                <Circle size={8} className="animate-pulse" />
                <span>Checking...</span>
              </div>
            ) : connected ? (
              <div className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <Circle size={8} className="fill-current" />
                <span>Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                <AlertCircle size={16} />
                <span>Offline</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
