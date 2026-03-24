import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Plus, Trash2, Pencil, Check, X, ChevronUp, ChevronDown,
  Film, Clock, Search, Flag, Save, Play, AlertCircle, Loader2, Scan,
} from 'lucide-react'
import { apiClient } from '@/api/client'
import { Compilation, CompilationClip, Video, LoopMarker } from '@/types'

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function CompilationEditor() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [compilation, setCompilation] = useState<Compilation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Title editing
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')

  // Add clip modal
  const [showAddClip, setShowAddClip] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Video[]>([])
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null)
  const [clipMarkA, setClipMarkA] = useState<number | null>(null)
  const [clipMarkB, setClipMarkB] = useState<number | null>(null)
  const [clipLabel, setClipLabel] = useState('')
  const [addingClip, setAddingClip] = useState(false)
  const clipVideoRef = useRef<HTMLVideoElement>(null)

  // Import from loops modal
  const [showLoopImport, setShowLoopImport] = useState(false)
  const [loopVideos, setLoopVideos] = useState<{ video: Video; loops: LoopMarker[] }[]>([])
  const [selectedLoops, setSelectedLoops] = useState<Set<number>>(new Set())
  const [importingLoops, setImportingLoops] = useState(false)

  // Clip editing
  const [editingClipId, setEditingClipId] = useState<number | null>(null)
  const [clipLabelDraft, setClipLabelDraft] = useState('')

  // Preview
  const [previewClip, setPreviewClip] = useState<CompilationClip | null>(null)
  const previewVideoRef = useRef<HTMLVideoElement>(null)

  // Analyze & Render
  const [analysis, setAnalysis] = useState<any>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [renderMode, setRenderMode] = useState<string | null>(null)
  const [rendering, setRendering] = useState(false)
  const [renderError, setRenderError] = useState<string | null>(null)

  const fetchCompilation = () => {
    if (!id) return
    apiClient.getCompilation(id)
      .then((c) => { setCompilation(c); setError(null) })
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchCompilation() }, [id])

  // Preview loop playback
  useEffect(() => {
    const video = previewVideoRef.current
    if (!video || !previewClip) return
    const onTimeUpdate = () => {
      if (video.currentTime >= previewClip.end_secs) {
        video.currentTime = previewClip.start_secs
      }
    }
    video.addEventListener('timeupdate', onTimeUpdate)
    return () => video.removeEventListener('timeupdate', onTimeUpdate)
  }, [previewClip])

  // Poll render status
  useEffect(() => {
    if (!compilation || compilation.status !== 'rendering') return
    setRendering(true)
    const interval = setInterval(async () => {
      try {
        const updated = await apiClient.getCompilation(compilation.id)
        setCompilation(updated)
        if (updated.status === 'completed' || updated.status === 'failed') {
          setRendering(false)
          if (updated.status === 'failed') setRenderError(updated.error_message || 'Render failed')
        }
      } catch {}
    }, 2000)
    return () => clearInterval(interval)
  }, [compilation?.status])

  // --- Handlers ---

  const handleSaveTitle = async () => {
    if (!compilation || !titleDraft.trim()) return
    try {
      const updated = await apiClient.updateCompilation(compilation.id, { title: titleDraft.trim() })
      setCompilation(updated)
      setEditingTitle(false)
    } catch {}
  }

  const handleMoveClip = async (clipId: number, direction: 'up' | 'down') => {
    if (!compilation) return
    const clips = [...compilation.clips]
    const idx = clips.findIndex((c) => c.id === clipId)
    if (idx < 0) return
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1
    if (swapIdx < 0 || swapIdx >= clips.length) return

    const newOrder = clips.map((c) => c.id)
    ;[newOrder[idx], newOrder[swapIdx]] = [newOrder[swapIdx], newOrder[idx]]

    try {
      await apiClient.reorderClips(compilation.id, newOrder)
      fetchCompilation()
    } catch {}
  }

  const handleDeleteClip = async (clipId: number) => {
    if (!compilation) return
    try {
      await apiClient.deleteClip(compilation.id, clipId)
      if (previewClip?.id === clipId) setPreviewClip(null)
      fetchCompilation()
    } catch {}
  }

  const handleRenameClip = async (clip: CompilationClip) => {
    if (!compilation || !clipLabelDraft.trim()) { setEditingClipId(null); return }
    try {
      await apiClient.updateClip(compilation.id, clip.id, { label: clipLabelDraft.trim() })
      setEditingClipId(null)
      fetchCompilation()
    } catch {}
  }

  const handlePreviewClip = (clip: CompilationClip) => {
    setPreviewClip(clip)
    // Wait for video to load then seek
    setTimeout(() => {
      if (previewVideoRef.current) {
        previewVideoRef.current.currentTime = clip.start_secs
        previewVideoRef.current.play().catch(() => {})
      }
    }, 300)
  }

  // --- Add Clip Modal ---

  const handleSearchVideos = async () => {
    if (!searchQuery.trim()) return
    try {
      const resp = await apiClient.searchVideos(searchQuery.trim())
      setSearchResults(resp.items.filter((v) => v.status === 'completed'))
    } catch {}
  }

  const handleSelectVideo = (video: Video) => {
    setSelectedVideo(video)
    setClipMarkA(null)
    setClipMarkB(null)
    setClipLabel('')
  }

  const handleAddClip = async () => {
    if (!compilation || !selectedVideo || clipMarkA === null || clipMarkB === null) return
    setAddingClip(true)
    try {
      await apiClient.addClip(compilation.id, {
        source_video_id: selectedVideo.id,
        start_secs: Math.round(clipMarkA * 100) / 100,
        end_secs: Math.round(clipMarkB * 100) / 100,
        label: clipLabel.trim() || undefined,
      })
      setShowAddClip(false)
      setSelectedVideo(null)
      setSearchQuery('')
      setSearchResults([])
      fetchCompilation()
    } catch {} finally {
      setAddingClip(false)
    }
  }

  // --- Analyze & Render ---

  const handleAnalyze = async () => {
    if (!compilation) return
    setAnalyzing(true)
    setAnalysis(null)
    setRenderError(null)
    try {
      const result = await apiClient.analyzeCompilation(compilation.id)
      setAnalysis(result)
      // Pre-select recommended mode
      const rec = result.options?.find((o: any) => o.recommended)
      setRenderMode(rec?.mode || 'reencode')
    } catch (err: any) {
      setRenderError(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleRender = async () => {
    if (!compilation || !renderMode) return
    setRendering(true)
    setRenderError(null)
    try {
      await apiClient.renderCompilation(compilation.id, renderMode)
      // Status polling will pick up progress
      fetchCompilation()
    } catch (err: any) {
      setRenderError(err.response?.data?.detail || 'Failed to start render')
      setRendering(false)
    }
  }

  // --- Loop Import Modal ---

  const openLoopImport = async () => {
    setShowLoopImport(true)
    setSelectedLoops(new Set())
    try {
      const videos = await apiClient.getVideos({ per_page: 100 })
      const results: { video: Video; loops: LoopMarker[] }[] = []
      for (const video of videos.items.filter((v) => v.status === 'completed')) {
        const loops = await apiClient.getLoopMarkers(video.id)
        if (loops.length > 0) results.push({ video, loops })
      }
      setLoopVideos(results)
    } catch {}
  }

  const toggleLoop = (loopId: number) => {
    setSelectedLoops((prev) => {
      const next = new Set(prev)
      if (next.has(loopId)) next.delete(loopId)
      else next.add(loopId)
      return next
    })
  }

  const handleImportLoops = async () => {
    if (!compilation || selectedLoops.size === 0) return
    setImportingLoops(true)
    try {
      for (const loopId of selectedLoops) {
        await apiClient.importLoopAsClip(compilation.id, loopId)
      }
      setShowLoopImport(false)
      setSelectedLoops(new Set())
      fetchCompilation()
    } catch {} finally {
      setImportingLoops(false)
    }
  }

  // --- Rendering ---

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-24" />
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64" />
        <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    )
  }

  if (error || !compilation) {
    return (
      <div className="space-y-4">
        <button onClick={() => navigate('/compilations')} className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
          <ArrowLeft size={20} /> Back
        </button>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 flex items-center gap-3">
          <AlertCircle size={20} className="text-red-600" />
          <p className="text-red-700 dark:text-red-400">{error || 'Compilation not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <button onClick={() => navigate('/compilations')} className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium transition-colors">
        <ArrowLeft size={20} /> Back to Compilations
      </button>

      <div className="flex items-center gap-3">
        <Film size={24} className="text-indigo-500" />
        {editingTitle ? (
          <div className="flex items-center gap-2 flex-1">
            <input
              type="text"
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveTitle(); if (e.key === 'Escape') setEditingTitle(false) }}
              autoFocus
              className="flex-1 px-3 py-1 text-xl font-bold rounded-lg border border-indigo-300 dark:border-indigo-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
            />
            <button onClick={handleSaveTitle} className="p-1 text-green-600"><Check size={20} /></button>
            <button onClick={() => setEditingTitle(false)} className="p-1 text-gray-400"><X size={20} /></button>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{compilation.title}</h1>
            <button onClick={() => { setEditingTitle(true); setTitleDraft(compilation.title) }} className="p-1 text-gray-400 hover:text-indigo-600"><Pencil size={16} /></button>
          </>
        )}
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
        <span>{compilation.clip_count} clip{compilation.clip_count !== 1 ? 's' : ''}</span>
        {compilation.estimated_duration_secs > 0 && (
          <span className="flex items-center gap-1"><Clock size={14} /> {formatTime(compilation.estimated_duration_secs)}</span>
        )}
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Clip list */}
        <div className="lg:col-span-3 space-y-3">
          {compilation.clips.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
              <p className="text-gray-500 dark:text-gray-400">No clips yet. Add clips from your video library.</p>
            </div>
          ) : (
            compilation.clips.map((clip, idx) => (
              <div
                key={clip.id}
                className={`bg-white dark:bg-gray-800 rounded-lg border p-3 transition-colors ${
                  previewClip?.id === clip.id
                    ? 'border-indigo-400 dark:border-indigo-600'
                    : 'border-gray-200 dark:border-gray-700'
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Reorder buttons */}
                  <div className="flex flex-col gap-0.5 pt-1">
                    <button
                      onClick={() => handleMoveClip(clip.id, 'up')}
                      disabled={idx === 0}
                      className="p-0.5 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronUp size={14} />
                    </button>
                    <button
                      onClick={() => handleMoveClip(clip.id, 'down')}
                      disabled={idx === compilation.clips.length - 1}
                      className="p-0.5 text-gray-400 hover:text-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <ChevronDown size={14} />
                    </button>
                  </div>

                  {/* Clip info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-gray-400 dark:text-gray-500 w-5">{clip.position}.</span>
                      {editingClipId === clip.id ? (
                        <div className="flex items-center gap-1 flex-1">
                          <input
                            type="text"
                            value={clipLabelDraft}
                            onChange={(e) => setClipLabelDraft(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleRenameClip(clip); if (e.key === 'Escape') setEditingClipId(null) }}
                            autoFocus
                            className="flex-1 px-2 py-0.5 text-sm rounded border border-indigo-300 dark:border-indigo-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none"
                          />
                          <button onClick={() => handleRenameClip(clip)} className="p-0.5 text-green-600"><Check size={14} /></button>
                          <button onClick={() => setEditingClipId(null)} className="p-0.5 text-gray-400"><X size={14} /></button>
                        </div>
                      ) : (
                        <span className="font-medium text-gray-900 dark:text-white text-sm truncate">
                          {clip.label || 'Untitled clip'}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {clip.source_video_title || 'Unknown video'}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      {formatTime(clip.start_secs)} → {formatTime(clip.end_secs)} ({formatTime(clip.duration_secs)})
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => handlePreviewClip(clip)} className="p-1.5 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded transition-colors" title="Preview">
                      <Play size={14} />
                    </button>
                    <button onClick={() => { setEditingClipId(clip.id); setClipLabelDraft(clip.label || '') }} className="p-1.5 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded transition-colors" title="Rename">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => handleDeleteClip(clip.id)} className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors" title="Remove">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}

          {/* Add clip buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowAddClip(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
            >
              <Plus size={16} /> Add Clip
            </button>
            <button
              onClick={openLoopImport}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <Flag size={16} /> From Loop Markers
            </button>
          </div>

          {/* Render Section */}
          {compilation.clips.length > 0 && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-3">
              {/* Completed: show player */}
              {compilation.status === 'completed' && compilation.output_path && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800 p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-sm font-semibold text-green-700 dark:text-green-400">Rendered successfully</span>
                    {compilation.duration_secs && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">({formatTime(compilation.duration_secs)})</span>
                    )}
                  </div>
                  <div className="bg-black rounded-lg overflow-hidden">
                    <video className="w-full h-auto" controls>
                      <source src={apiClient.getCompilationStreamUrl(compilation.id)} type="video/mp4" />
                    </video>
                  </div>
                  <button
                    onClick={() => { setAnalysis(null); handleAnalyze() }}
                    className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    Re-render with different settings
                  </button>
                </div>
              )}

              {/* Rendering: show progress */}
              {compilation.status === 'rendering' && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-blue-200 dark:border-blue-800 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Loader2 size={16} className="text-blue-500 animate-spin" />
                    <span className="text-sm font-semibold text-blue-700 dark:text-blue-400">Rendering...</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }} />
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">This may take a few minutes for re-encoded compilations</p>
                </div>
              )}

              {/* Failed: show error */}
              {compilation.status === 'failed' && compilation.error_message && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle size={18} className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-red-700 dark:text-red-400">Render failed</p>
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">{compilation.error_message}</p>
                  </div>
                </div>
              )}

              {renderError && compilation.status !== 'failed' && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-400">
                  {renderError}
                </div>
              )}

              {/* Analyze & Render controls (draft or failed state) */}
              {(compilation.status === 'draft' || compilation.status === 'failed') && !rendering && (
                <>
                  {!analysis ? (
                    <button
                      onClick={handleAnalyze}
                      disabled={analyzing}
                      className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                    >
                      {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Scan size={16} />}
                      {analyzing ? 'Analyzing...' : 'Analyze Compatibility'}
                    </button>
                  ) : (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        {analysis.compatible ? (
                          <span className="text-sm text-green-700 dark:text-green-400 font-medium">All clips compatible</span>
                        ) : (
                          <span className="text-sm text-amber-700 dark:text-amber-400 font-medium">Compatibility issue detected</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{analysis.reason}</p>

                      <div className="space-y-2">
                        {analysis.options?.map((opt: any) => (
                          <label
                            key={opt.mode}
                            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                              renderMode === opt.mode
                                ? 'border-indigo-400 dark:border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20'
                                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                            }`}
                          >
                            <input
                              type="radio"
                              name="renderMode"
                              value={opt.mode}
                              checked={renderMode === opt.mode}
                              onChange={() => setRenderMode(opt.mode)}
                              className="mt-0.5"
                            />
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-gray-900 dark:text-white">{opt.label}</span>
                                {opt.recommended && (
                                  <span className="text-xs px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400 rounded">recommended</span>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{opt.description}</p>
                              <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">Estimated: {opt.estimated_time}</p>
                            </div>
                          </label>
                        ))}
                      </div>

                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={handleRender}
                          disabled={!renderMode}
                          className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
                        >
                          <Play size={16} />
                          Render Compilation
                        </button>
                        <button
                          onClick={() => setAnalysis(null)}
                          className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Right: Preview */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sticky top-20">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Preview</h3>
            {previewClip ? (
              <div className="space-y-2">
                <div className="bg-black rounded-lg overflow-hidden">
                  <video
                    ref={previewVideoRef}
                    className="w-full h-auto"
                    controls
                    key={previewClip.source_video_id}
                  >
                    <source src={apiClient.getVideoStreamUrl(previewClip.source_video_id)} type="video/mp4" />
                  </video>
                </div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{previewClip.label || 'Untitled clip'}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {previewClip.source_video_title} &middot; {formatTime(previewClip.start_secs)} → {formatTime(previewClip.end_secs)}
                </p>
              </div>
            ) : (
              <div className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                <p className="text-sm text-gray-400 dark:text-gray-500">Select a clip to preview</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Clip Modal */}
      {showAddClip && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowAddClip(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Add Clip</h2>
              <button onClick={() => { setShowAddClip(false); setSelectedVideo(null); setSearchResults([]) }} className="p-1 text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            <div className="p-4 space-y-4">
              {!selectedVideo ? (
                <>
                  {/* Search */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 relative">
                      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearchVideos()}
                        placeholder="Search your videos..."
                        autoFocus
                        className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <button onClick={handleSearchVideos} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors">Search</button>
                  </div>

                  {/* Results */}
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {searchResults.map((video) => (
                      <div
                        key={video.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                        onClick={() => handleSelectVideo(video)}
                      >
                        <div className="w-16 h-10 bg-gray-200 dark:bg-gray-600 rounded flex-shrink-0 overflow-hidden">
                          {video.thumbnail_path && <img src={video.thumbnail_path} alt="" className="w-full h-full object-cover" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{video.title}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">{video.platform} &middot; {video.duration_secs ? formatTime(video.duration_secs) : '?'}</p>
                        </div>
                      </div>
                    ))}
                    {searchResults.length === 0 && searchQuery && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No videos found. Try a different search.</p>
                    )}
                  </div>
                </>
              ) : (
                <>
                  {/* Selected video with A/B markers */}
                  <button onClick={() => setSelectedVideo(null)} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
                    ← Choose a different video
                  </button>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedVideo.title}</p>

                  <div className="bg-black rounded-lg overflow-hidden">
                    <video ref={clipVideoRef} className="w-full h-auto" controls>
                      <source src={apiClient.getVideoStreamUrl(selectedVideo.id)} type="video/mp4" />
                    </video>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => { if (clipVideoRef.current) setClipMarkA(clipVideoRef.current.currentTime) }}
                      className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                        clipMarkA !== null
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
                      }`}
                    >
                      <Flag size={14} />
                      {clipMarkA !== null ? `A: ${formatTime(clipMarkA)}` : 'Set A'}
                    </button>
                    <button
                      onClick={() => {
                        if (clipVideoRef.current && clipMarkA !== null) {
                          const b = clipVideoRef.current.currentTime
                          if (b > clipMarkA) setClipMarkB(b)
                        }
                      }}
                      disabled={clipMarkA === null}
                      className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                        clipMarkB !== null
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700'
                          : clipMarkA !== null
                            ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                      }`}
                    >
                      <Flag size={14} />
                      {clipMarkB !== null ? `B: ${formatTime(clipMarkB)}` : 'Set B'}
                    </button>
                  </div>

                  <input
                    type="text"
                    value={clipLabel}
                    onChange={(e) => setClipLabel(e.target.value)}
                    placeholder="Label (optional)"
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
                  />

                  <div className="flex justify-end gap-2">
                    <button onClick={() => { setShowAddClip(false); setSelectedVideo(null) }} className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">Cancel</button>
                    <button
                      onClick={handleAddClip}
                      disabled={addingClip || clipMarkA === null || clipMarkB === null}
                      className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                    >
                      <Save size={16} />
                      {addingClip ? 'Adding...' : 'Add to Compilation'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loop Import Modal */}
      {showLoopImport && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowLoopImport(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">Import from Loop Markers</h2>
              <button onClick={() => setShowLoopImport(false)} className="p-1 text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>

            <div className="p-4 space-y-4">
              {loopVideos.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">No videos with saved loop markers found.</p>
              ) : (
                loopVideos.map(({ video, loops }) => (
                  <div key={video.id}>
                    <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">{video.title}</p>
                    <div className="space-y-1 ml-4">
                      {loops.map((loop) => (
                        <label key={loop.id} className="flex items-center gap-2 text-sm cursor-pointer py-1">
                          <input
                            type="checkbox"
                            checked={selectedLoops.has(loop.id)}
                            onChange={() => toggleLoop(loop.id)}
                            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                          />
                          <span className="text-gray-700 dark:text-gray-300">{loop.label}</span>
                          <span className="text-gray-400 dark:text-gray-500">({formatTime(loop.start_secs)} → {formatTime(loop.end_secs)})</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                <button onClick={() => setShowLoopImport(false)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">Cancel</button>
                <button
                  onClick={handleImportLoops}
                  disabled={importingLoops || selectedLoops.size === 0}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                >
                  {importingLoops ? 'Importing...' : `Import ${selectedLoops.size} selected`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
