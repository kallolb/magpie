import DownloadForm from '@/components/video/DownloadForm'
import { useAppStore } from '@/store'
import { useEffect } from 'react'
import VideoGrid from '@/components/video/VideoGrid'

export default function Download() {
  const { videos, fetchVideos } = useAppStore()

  useEffect(() => {
    fetchVideos(1, 10)
  }, [fetchVideos])

  // Sort videos by download_date, most recent first
  const recentVideos = [...videos].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return (
    <div className="space-y-8">
      {/* Main Download Form */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
          Download Video
        </h1>
        <DownloadForm />
      </div>

      {/* Recent Downloads */}
      {recentVideos.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            Recent Downloads
          </h2>
          <VideoGrid videos={recentVideos.slice(0, 12)} />
        </div>
      )}
    </div>
  )
}
