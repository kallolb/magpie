import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, AlertCircle } from 'lucide-react'
import { Video } from '@/types'
import { apiClient } from '@/api/client'
import VideoDetail from '@/components/video/VideoDetail'

export default function VideoView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return

    const fetchVideo = async () => {
      try {
        const data = await apiClient.getVideo(id)
        setVideo(data)
        setError(null)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load video')
      } finally {
        setLoading(false)
      }
    }

    fetchVideo()
  }, [id])

  if (loading) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
        >
          <ArrowLeft size={20} />
          Back
        </button>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
          <div className="aspect-video bg-gray-200 dark:bg-gray-700 rounded mb-6" />
          <div className="space-y-4">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !video) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
        >
          <ArrowLeft size={20} />
          Back
        </button>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <div className="flex items-start gap-4">
            <AlertCircle size={24} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-1" />
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                Error Loading Video
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mt-2">
                {error || 'Video not found'}
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium transition-colors"
      >
        <ArrowLeft size={20} />
        Back
      </button>
      <VideoDetail video={video} onUpdate={setVideo} />
    </div>
  )
}
