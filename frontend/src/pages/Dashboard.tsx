import { useEffect, useState } from 'react'
import {
  Video as VideoIcon,
  HardDrive,
  FolderOpen,
  Tag,
  TrendingUp,
} from 'lucide-react'
import { useAppStore } from '@/store'
import { apiClient } from '@/api/client'
import { StorageStats } from '@/types'
import DownloadForm from '@/components/video/DownloadForm'
import VideoGrid from '@/components/video/VideoGrid'

export default function Dashboard() {
  const {
    videos,
    totalVideos,
    categories,
    tags,
    activeDownloads,
    fetchVideos,
    fetchCategories,
    fetchTags,
  } = useAppStore()
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null)

  useEffect(() => {
    fetchVideos(1, 10)
    fetchCategories()
    fetchTags()

    const loadStats = async () => {
      try {
        const stats = await apiClient.getStorageStats()
        setStorageStats(stats)
      } catch (error) {
        console.error('Failed to load storage stats:', error)
      }
    }
    loadStats()
  }, [fetchVideos, fetchCategories, fetchTags])

  const formatBytes = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  const downloads = Array.from(activeDownloads.values())

  return (
    <div className="space-y-8">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Total Videos
              </p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                {totalVideos}
              </p>
            </div>
            <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
              <VideoIcon size={24} className="text-indigo-600 dark:text-indigo-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Storage Used
              </p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                {storageStats ? formatBytes(storageStats.used_bytes) : '--'}
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <HardDrive size={24} className="text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Categories
              </p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                {categories.length}
              </p>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <FolderOpen size={24} className="text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Tags
              </p>
              <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">
                {tags.length}
              </p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Tag size={24} className="text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Active Downloads */}
      {downloads.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <TrendingUp size={24} />
            Active Downloads
          </h2>

          <div className="space-y-4">
            {downloads.map((download) => (
              <div key={download.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {download.video?.title || 'Downloading...'}
                  </span>
                  <span className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                    {download.progress}%
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-600 transition-all"
                    style={{ width: `${download.progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                  Status: {download.status}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Download Form */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Quick Download
        </h2>
        <DownloadForm />
      </div>

      {/* Recent Videos */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Recent Downloads
        </h2>
        {videos.length > 0 ? (
          <VideoGrid videos={videos.slice(0, 8)} />
        ) : (
          <p className="text-gray-600 dark:text-gray-400">
            No videos downloaded yet. Start by downloading one above!
          </p>
        )}
      </div>
    </div>
  )
}
