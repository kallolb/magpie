import { useState, useEffect } from 'react'
import { Plus, Trash2, AlertCircle } from 'lucide-react'
import { useTags } from '@/hooks/useTags'
import TagBadge from './TagBadge'

export default function TagManager() {
  const { tags, addTag, removeTag, loadTags } = useTags()
  const [newTagName, setNewTagName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadTags()
  }, [loadTags])

  const handleAddTag = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTagName.trim()) return

    setLoading(true)
    setError(null)

    try {
      await addTag(newTagName)
      setNewTagName('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create tag')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteTag = async (id: number) => {
    setDeleting(true)
    setError(null)

    try {
      await removeTag(id)
      setDeleteConfirm(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete tag')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Create New Tag */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Create New Tag
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
            <AlertCircle size={18} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}

        <form onSubmit={handleAddTag} className="flex gap-2">
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="Enter tag name..."
            className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={!newTagName.trim() || loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
          >
            <Plus size={18} />
            Create
          </button>
        </form>
      </div>

      {/* Tags List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          All Tags ({tags.length})
        </h2>

        {tags.length === 0 ? (
          <p className="text-gray-600 dark:text-gray-400">No tags yet. Create one to get started.</p>
        ) : (
          <div className="space-y-2">
            {tags.map((tag) => (
              <div
                key={tag.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <TagBadge name={tag.name} />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {tag.video_count} video{tag.video_count !== 1 ? 's' : ''}
                  </span>
                </div>

                {deleteConfirm === tag.id ? (
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleDeleteTag(tag.id)}
                      disabled={deleting}
                      className="px-2 py-1 text-sm bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded transition-colors"
                    >
                      {deleting ? 'Deleting...' : 'Confirm'}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-500 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(tag.id)}
                    className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
