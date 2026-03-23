import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Youtube, Instagram, Trash2 } from 'lucide-react'
import { Video } from '@/types'
import { apiClient } from '@/api/client'
import TagBadge from '@/components/tags/TagBadge'

interface VideoCardProps {
  video: Video
  onDelete?: () => void
}

export default function VideoCard({ video, onDelete }: VideoCardProps) {
  const navigate = useNavigate()
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleClick = () => {
    if (showDeleteConfirm) return
    navigate(`/video/${video.id}`)
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!showDeleteConfirm) {
      setShowDeleteConfirm(true)
      return
    }
    setDeleting(true)
    try {
      await apiClient.deleteVideo(video.id)
      onDelete?.()
    } catch (err) {
      console.error('Failed to delete video:', err)
    } finally {
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(false)
  }

  const getPlatformIcon = () => {
    if (video.platform === 'youtube') {
      return <Youtube size={16} className="text-red-600" />
    }
    if (video.platform === 'instagram') {
      return <Instagram size={16} className="text-pink-600" />
    }
    return null
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs
        .toString()
        .padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString()
  }

  return (
    <div
      onClick={handleClick}
      className="group cursor-pointer rounded-lg overflow-hidden bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-shadow"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-200 dark:bg-gray-700 overflow-hidden">
        {video.thumbnail_path ? (
          <img
            src={video.thumbnail_path}
            alt={video.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-300 to-gray-400 dark:from-gray-600 dark:to-gray-700">
            <Play size={40} className="text-gray-500 dark:text-gray-400" />
          </div>
        )}

        {/* Duration Badge */}
        {(video.duration_secs || 0) > 0 && (
          <div className="absolute bottom-2 right-2 bg-black/75 px-2 py-1 rounded text-xs font-medium text-white">
            {formatDuration(video.duration_secs || 0)}
          </div>
        )}

        {/* Overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
          <Play size={48} className="text-white opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Title */}
        <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-2 mb-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
          {video.title}
        </h3>

        {/* Uploader and Platform */}
        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 mb-2">
          {getPlatformIcon()}
          <span className="truncate">{video.uploader}</span>
        </div>

        {/* Category Badge */}
        {video.category && (
          <div className="inline-block mb-2 px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded text-xs font-medium">
            {video.category}
          </div>
        )}

        {/* Tags */}
        {video.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {video.tags.slice(0, 3).map((tag) => (
              <TagBadge key={tag} name={tag} />
            ))}
            {video.tags.length > 3 && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                +{video.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700 pt-2 mt-2">
          <span>{formatDate(video.created_at)}</span>
          <div className="flex items-center gap-2">
            <span>{video.resolution}</span>
            <button
              onClick={handleDelete}
              className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors"
              title="Delete video"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>

        {/* Delete Confirmation */}
        {showDeleteConfirm && (
          <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs">
            <p className="text-red-700 dark:text-red-400 mb-2">Delete this video?</p>
            <div className="flex gap-2">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-2 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded transition-colors"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
              <button
                onClick={cancelDelete}
                className="px-2 py-1 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
