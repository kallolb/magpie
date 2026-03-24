import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Copy,
  ExternalLink,
  Edit2,
  Trash2,
  Save,
  X as XIcon,
  AlertCircle,
} from 'lucide-react'
import { Video } from '@/types'
import { apiClient } from '@/api/client'
import VideoPlayer from './VideoPlayer'
import TagBadge from '@/components/tags/TagBadge'
import TagInput, { TagInputHandle } from '@/components/tags/TagInput'
import { useAppStore } from '@/store'

interface VideoDetailProps {
  video: Video
  onUpdate?: (video: Video) => void
}

export default function VideoDetail({ video, onUpdate }: VideoDetailProps) {
  const navigate = useNavigate()
  const { categories, fetchCategories, fetchVideos, fetchTags } = useAppStore()
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(video.title)
  const [editCategory, setEditCategory] = useState(video.category || '')
  const [editTags, setEditTags] = useState(video.tags)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const tagInputRef = useRef<TagInputHandle>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deletionCheck, setDeletionCheck] = useState<any>(null)
  const [checkingDeletion, setCheckingDeletion] = useState(false)

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`
    }
    return `${minutes}m ${secs}s`
  }

  const handleSave = async () => {
    // Commit any pending text in the tag input
    const finalTags = tagInputRef.current?.flush() ?? editTags
    setSaving(true)
    setError(null)

    try {
      const updated = await apiClient.updateVideo(video.id, {
        title: editTitle,
        category: editCategory || undefined,
        tags: finalTags,
      })
      onUpdate?.(updated)
      setIsEditing(false)
      fetchVideos()
      fetchTags()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    setError(null)

    try {
      await apiClient.deleteVideo(video.id)
      await fetchVideos()
      navigate('/browse')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete video')
      setDeleting(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="space-y-6">
      {/* Video Player */}
      <VideoPlayer
        videoId={video.id}
        title={video.title}
        thumbnailUrl={video.thumbnail_path}
      />

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
          <AlertCircle size={20} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        {isEditing ? (
          /* Edit Mode */
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Title
              </label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Category
              </label>
              <select
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">Uncategorized</option>
                {categories.map((cat) => (
                  <option key={cat.name} value={cat.name}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tags
              </label>
              <TagInput ref={tagInputRef} value={editTags} onChange={setEditTags} />
            </div>

            <div className="flex gap-2 pt-4">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
              >
                <Save size={18} />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                onClick={() => {
                  setIsEditing(false)
                  setEditTitle(video.title)
                  setEditCategory(video.category || '')
                  setEditTags(video.tags)
                }}
                className="flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <XIcon size={18} />
                Cancel
              </button>
            </div>
          </div>
        ) : (
          /* View Mode */
          <>
            <div className="flex items-start justify-between mb-4">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white pr-4">
                {video.title}
              </h1>
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-3 py-2 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
              >
                <Edit2 size={18} />
              </button>
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Platform
                </p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                  {video.platform}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Duration
                </p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatDuration(video.duration_secs || 0)}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Resolution
                </p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {video.resolution}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  File Size
                </p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatFileSize(video.file_size_bytes || 0)}
                </p>
              </div>
            </div>

            {/* Uploader and Dates */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6 pb-6 border-b border-gray-200 dark:border-gray-700">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Uploader</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {video.uploader}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Upload Date</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {formatDate(video.upload_date || video.created_at)}
                </p>
              </div>

              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Download Date</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {formatDate(video.created_at)}
                </p>
              </div>
            </div>

            {/* Category and Tags */}
            <div className="mb-6">
              {video.category && (
                <div className="mb-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Category</p>
                  <div className="inline-block px-3 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded-lg font-medium">
                    {video.category}
                  </div>
                </div>
              )}

              {video.tags.length > 0 && (
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {video.tags.map((tag) => (
                      <TagBadge key={tag} name={tag} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Source URL */}
            <div className="mb-6 pb-6 border-b border-gray-200 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Source URL</p>
              <div className="flex items-center gap-2">
                <a
                  href={video.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-indigo-600 dark:text-indigo-400 hover:underline break-all"
                >
                  {video.source_url}
                </a>
                <button
                  onClick={() => copyToClipboard(video.source_url)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Copy URL"
                >
                  <Copy size={18} />
                </button>
                <a
                  href={video.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Open in new tab"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>

            {/* File Path */}
            <div className="mb-6">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">File Path</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded text-sm break-all">
                  {video.file_path}
                </code>
                <button
                  onClick={() => copyToClipboard(video.file_path || '')}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Copy path"
                >
                  <Copy size={18} />
                </button>
              </div>
            </div>

            {/* Delete Button */}
            {!showDeleteConfirm && (
              <button
                onClick={async () => {
                  setCheckingDeletion(true)
                  try {
                    const check = await apiClient.checkVideoDeletion(video.id)
                    setDeletionCheck(check)
                  } catch {}
                  setCheckingDeletion(false)
                  setShowDeleteConfirm(true)
                }}
                disabled={checkingDeletion}
                className="flex items-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                <Trash2 size={18} />
                {checkingDeletion ? 'Checking...' : 'Delete Video'}
              </button>
            )}

            {/* Delete Confirmation */}
            {showDeleteConfirm && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                {deletionCheck?.referenced && (
                  <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                    <p className="text-amber-800 dark:text-amber-300 text-sm font-medium mb-1">
                      This video is used in {deletionCheck.compilation_count} compilation{deletionCheck.compilation_count !== 1 ? 's' : ''}:
                    </p>
                    <ul className="text-xs text-amber-700 dark:text-amber-400 list-disc list-inside">
                      {deletionCheck.compilations.map((c: any) => (
                        <li key={c.id}>{c.title}</li>
                      ))}
                    </ul>
                    <p className="text-xs text-amber-600 dark:text-amber-500 mt-1">
                      Deleting will make those clips unrenderable.
                    </p>
                  </div>
                )}
                <p className="text-red-900 dark:text-red-300 font-medium mb-3">
                  Are you sure you want to delete this video? This action cannot be undone.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                  >
                    {deleting ? 'Deleting...' : 'Delete'}
                  </button>
                  <button
                    onClick={() => { setShowDeleteConfirm(false); setDeletionCheck(null) }}
                    className="px-4 py-2 border border-red-300 dark:border-red-700 text-red-900 dark:text-red-300 rounded-lg font-medium hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
