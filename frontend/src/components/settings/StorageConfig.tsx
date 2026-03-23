import { useEffect, useState } from 'react'
import { HardDrive } from 'lucide-react'
import { apiClient } from '@/api/client'
import { StorageStats } from '@/types'

export default function StorageConfig() {
  const [stats, setStats] = useState<StorageStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await apiClient.getStorageStats()
        setStats(data)
      } catch (error) {
        console.error('Failed to fetch storage stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatBytes = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded mb-4 w-1/3" />
        <div className="space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <p className="text-gray-600 dark:text-gray-400">
          Unable to load storage statistics
        </p>
      </div>
    )
  }

  const usagePercent = (stats.used_bytes / stats.total_bytes) * 100

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div className="flex items-center gap-3 mb-6">
        <HardDrive size={24} className="text-indigo-600 dark:text-indigo-400" />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Storage Configuration
        </h2>
      </div>

      <div className="space-y-6">
        {/* Storage Bars */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Storage Usage
            </span>
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {formatBytes(stats.used_bytes)} / {formatBytes(stats.total_bytes)}
            </span>
          </div>
          <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                usagePercent > 90
                  ? 'bg-red-500'
                  : usagePercent > 70
                    ? 'bg-yellow-500'
                    : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
            {usagePercent.toFixed(1)}% used
          </p>
        </div>

        {/* Free Space */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-1">
              Free Space
            </p>
            <p className="text-2xl font-bold text-green-900 dark:text-green-300">
              {formatBytes(stats.free_bytes)}
            </p>
          </div>

          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-1">
              Total Videos
            </p>
            <p className="text-2xl font-bold text-blue-900 dark:text-blue-300">
              {stats.video_count}
            </p>
          </div>
        </div>

        {/* Warning */}
        {usagePercent > 85 && (
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm font-medium text-yellow-900 dark:text-yellow-300">
              Storage usage is high. Consider deleting old videos or expanding your
              storage.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
