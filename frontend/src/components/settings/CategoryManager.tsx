import { useState, useEffect } from 'react'
import { Plus, Trash2, AlertCircle } from 'lucide-react'
import { useAppStore } from '@/store'
import { apiClient } from '@/api/client'

export default function CategoryManager() {
  const { categories, fetchCategories } = useAppStore()
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryDesc, setNewCategoryDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  const handleAddCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCategoryName.trim()) return

    setLoading(true)
    setError(null)

    try {
      await apiClient.createCategory(
        newCategoryName,
        newCategoryDesc || undefined
      )
      setNewCategoryName('')
      setNewCategoryDesc('')
      await fetchCategories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create category')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteCategory = async (name: string) => {
    setDeleting(true)
    setError(null)

    try {
      await apiClient.deleteCategory(name)
      setDeleteConfirm(null)
      await fetchCategories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete category')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Create New Category */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Create New Category
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
            <AlertCircle size={18} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          </div>
        )}

        <form onSubmit={handleAddCategory} className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
              placeholder="Category name..."
              className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <textarea
            value={newCategoryDesc}
            onChange={(e) => setNewCategoryDesc(e.target.value)}
            placeholder="Description (optional)..."
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={!newCategoryName.trim() || loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
          >
            <Plus size={18} />
            Create Category
          </button>
        </form>
      </div>

      {/* Categories List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          All Categories ({categories.length})
        </h2>

        {categories.length === 0 ? (
          <p className="text-gray-600 dark:text-gray-400">
            No categories yet. Create one to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {categories.map((category) => (
              <div
                key={category.name}
                className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">
                      {category.name}
                    </h3>
                    {category.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {category.description}
                      </p>
                    )}
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                      {category.video_count} video{category.video_count !== 1 ? 's' : ''}
                    </p>
                  </div>

                  {deleteConfirm === category.name ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleDeleteCategory(category.name)}
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
                      onClick={() => setDeleteConfirm(category.name)}
                      className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
