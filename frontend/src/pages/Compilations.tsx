import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Edit2, Film, Clock } from 'lucide-react'
import { apiClient } from '@/api/client'
import { Compilation } from '@/types'

function formatDuration(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  if (m === 0) return `${s}s`
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    rendering: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.draft}`}>
      {status}
    </span>
  )
}

export default function Compilations() {
  const navigate = useNavigate()
  const [compilations, setCompilations] = useState<Compilation[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchCompilations = () => {
    apiClient.getCompilations()
      .then(setCompilations)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCompilations() }, [])

  const handleCreate = async () => {
    if (!newTitle.trim()) return
    setCreating(true)
    try {
      const comp = await apiClient.createCompilation({ title: newTitle.trim() })
      setNewTitle('')
      setShowCreate(false)
      navigate(`/compilations/${comp.id}`)
    } catch {} finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    setDeleting(true)
    try {
      await apiClient.deleteCompilation(id)
      setCompilations((prev) => prev.filter((c) => c.id !== id))
      setDeleteId(null)
    } catch {} finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48" />
        {[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />)}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Compilations</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
        >
          <Plus size={18} />
          New Compilation
        </button>
      </div>

      {/* Create dialog */}
      {showCreate && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">New Compilation</h3>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Compilation title..."
              autoFocus
              className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newTitle.trim()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => { setShowCreate(false); setNewTitle('') }}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Compilation list */}
      {compilations.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
          <Film size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 dark:text-gray-400 text-lg">No compilations yet</p>
          <p className="text-gray-500 dark:text-gray-500 text-sm mt-1">Create one to start combining clips from your videos</p>
        </div>
      ) : (
        <div className="space-y-3">
          {compilations.map((comp) => (
            <div
              key={comp.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors"
            >
              <div className="flex items-start gap-3">
                {comp.thumbnail_path ? (
                  <div className="w-20 h-14 bg-gray-200 dark:bg-gray-700 rounded flex-shrink-0 overflow-hidden">
                    <img src={comp.thumbnail_path.startsWith('/') ? comp.thumbnail_path : `/api/${comp.thumbnail_path}`} alt="" className="w-full h-full object-cover" />
                  </div>
                ) : (
                  <div className="w-20 h-14 bg-gray-100 dark:bg-gray-700 rounded flex-shrink-0 flex items-center justify-center">
                    <Film size={20} className="text-gray-400" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Film size={14} className="text-indigo-500 flex-shrink-0" />
                    <h3 className="font-semibold text-gray-900 dark:text-white truncate">{comp.title}</h3>
                    <StatusBadge status={comp.status} />
                  </div>
                  {comp.description && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2 truncate">{comp.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    <span>{comp.clip_count} clip{comp.clip_count !== 1 ? 's' : ''}</span>
                    {comp.estimated_duration_secs > 0 && (
                      <span className="flex items-center gap-1">
                        <Clock size={12} />
                        {formatDuration(comp.estimated_duration_secs)}
                      </span>
                    )}
                    {comp.output_size_bytes && (
                      <span>{formatBytes(comp.output_size_bytes)}</span>
                    )}
                    <span>Updated {new Date(comp.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-4 flex-shrink-0">
                  <button
                    onClick={() => navigate(`/compilations/${comp.id}`)}
                    className="p-2 text-gray-500 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    title="Edit"
                  >
                    <Edit2 size={16} />
                  </button>
                  {deleteId === comp.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(comp.id)}
                        disabled={deleting}
                        className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded transition-colors"
                      >
                        {deleting ? '...' : 'Confirm'}
                      </button>
                      <button
                        onClick={() => setDeleteId(null)}
                        className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 rounded transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteId(comp.id)}
                      className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
