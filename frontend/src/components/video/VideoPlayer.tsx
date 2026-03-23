import { useRef, useState, useEffect } from 'react'
import { Repeat, Flag, Square, Trash2, Play, Save } from 'lucide-react'
import { apiClient } from '@/api/client'
import { LoopMarker } from '@/types'

interface VideoPlayerProps {
  videoId: string
  title?: string
  thumbnailUrl?: string
}

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function VideoPlayer({
  videoId,
  title: _title,
  thumbnailUrl,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [duration, setDuration] = useState(0)

  // Loop marker state
  const [loopMarkers, setLoopMarkers] = useState<LoopMarker[]>([])
  const [activeLoop, setActiveLoop] = useState<LoopMarker | null>(null)
  const [markA, setMarkA] = useState<number | null>(null)
  const [markB, setMarkB] = useState<number | null>(null)
  const [newLabel, setNewLabel] = useState('')
  const [saving, setSaving] = useState(false)

  // Load loop markers
  useEffect(() => {
    apiClient.getLoopMarkers(videoId).then(setLoopMarkers).catch(() => {})
  }, [videoId])

  // Loop playback logic
  useEffect(() => {
    const video = videoRef.current
    if (!video || !activeLoop) return

    const onTimeUpdate = () => {
      if (video.currentTime >= activeLoop.end_secs) {
        video.currentTime = activeLoop.start_secs
      }
    }

    video.addEventListener('timeupdate', onTimeUpdate)
    return () => video.removeEventListener('timeupdate', onTimeUpdate)
  }, [activeLoop])

  // Live preview loop for unsaved A-B marks
  useEffect(() => {
    const video = videoRef.current
    if (!video || activeLoop || markA === null || markB === null) return

    const onTimeUpdate = () => {
      if (video.currentTime >= markB) {
        video.currentTime = markA
      }
    }

    video.addEventListener('timeupdate', onTimeUpdate)
    return () => video.removeEventListener('timeupdate', onTimeUpdate)
  }, [markA, markB, activeLoop])

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget
    setError(`Error loading video: ${video.error?.message || 'Unknown error'}`)
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
    }
  }

  const handleSetA = () => {
    if (videoRef.current) {
      setMarkA(videoRef.current.currentTime)
      setMarkB(null)
      setActiveLoop(null)
    }
  }

  const handleSetB = () => {
    if (videoRef.current && markA !== null) {
      const b = videoRef.current.currentTime
      if (b > markA) {
        setMarkB(b)
        // Seek to A and start looping immediately
        videoRef.current.currentTime = markA
        if (videoRef.current.paused) videoRef.current.play()
      }
    }
  }

  const handleSaveLoop = async () => {
    if (markA === null || markB === null || !newLabel.trim()) return
    setSaving(true)
    try {
      const marker = await apiClient.createLoopMarker(videoId, {
        label: newLabel.trim(),
        start_secs: Math.round(markA * 100) / 100,
        end_secs: Math.round(markB * 100) / 100,
      })
      setLoopMarkers((prev) => [...prev, marker].sort((a, b) => a.start_secs - b.start_secs))
      setActiveLoop(marker)
      setMarkA(null)
      setMarkB(null)
      setNewLabel('')
    } catch {
      // keep state so user can retry
    } finally {
      setSaving(false)
    }
  }

  const handleActivateLoop = (marker: LoopMarker) => {
    setActiveLoop(marker)
    setMarkA(null)
    setMarkB(null)
    if (videoRef.current) {
      videoRef.current.currentTime = marker.start_secs
      if (videoRef.current.paused) videoRef.current.play()
    }
  }

  const handleStopLoop = () => {
    setActiveLoop(null)
    setMarkA(null)
    setMarkB(null)
  }

  const handleDeleteLoop = async (marker: LoopMarker) => {
    try {
      await apiClient.deleteLoopMarker(videoId, marker.id)
      setLoopMarkers((prev) => prev.filter((m) => m.id !== marker.id))
      if (activeLoop?.id === marker.id) setActiveLoop(null)
    } catch {}
  }

  const isLooping = activeLoop !== null || (markA !== null && markB !== null)

  return (
    <div className="space-y-3">
      {/* Video */}
      <div className="w-full bg-black rounded-lg overflow-hidden relative">
        {error ? (
          <div className="aspect-video flex flex-col items-center justify-center bg-gray-900 text-white">
            <svg className="w-16 h-16 mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-lg font-medium">{error}</p>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              className="w-full h-auto"
              controls
              poster={thumbnailUrl}
              onError={handleError}
              onLoadedMetadata={handleLoadedMetadata}
            >
              <source src={apiClient.getVideoStreamUrl(videoId)} type="video/mp4" />
              Your browser does not support the video tag.
            </video>

            {/* Loop region indicators on the video */}
            {duration > 0 && (
              <div className="absolute bottom-12 left-0 right-0 h-1 pointer-events-none">
                {loopMarkers.map((m) => (
                  <div
                    key={m.id}
                    className={`absolute h-full rounded ${
                      activeLoop?.id === m.id ? 'bg-green-400/60' : 'bg-blue-400/40'
                    }`}
                    style={{
                      left: `${(m.start_secs / duration) * 100}%`,
                      width: `${((m.end_secs - m.start_secs) / duration) * 100}%`,
                    }}
                  />
                ))}
                {markA !== null && markB !== null && !activeLoop && (
                  <div
                    className="absolute h-full rounded bg-yellow-400/50"
                    style={{
                      left: `${(markA / duration) * 100}%`,
                      width: `${((markB - markA) / duration) * 100}%`,
                    }}
                  />
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Loop Controls */}
      {!error && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-4">
          {/* A/B buttons and stop */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300 mr-1">
              <Repeat size={16} className="inline mr-1" />
              Loop
            </span>

            <button
              onClick={handleSetA}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                markA !== null
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <Flag size={14} />
              {markA !== null ? `A: ${formatTime(markA)}` : 'Set A'}
            </button>

            <button
              onClick={handleSetB}
              disabled={markA === null}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                markB !== null
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700'
                  : markA !== null
                    ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
              }`}
            >
              <Flag size={14} />
              {markB !== null ? `B: ${formatTime(markB)}` : 'Set B'}
            </button>

            {isLooping && (
              <button
                onClick={handleStopLoop}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
              >
                <Square size={14} />
                Stop Loop
              </button>
            )}
          </div>

          {/* Save new loop */}
          {markA !== null && markB !== null && !activeLoop && (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="Label (e.g. Chorus, Verse 1)"
                className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500"
                onKeyDown={(e) => e.key === 'Enter' && handleSaveLoop()}
              />
              <button
                onClick={handleSaveLoop}
                disabled={saving || !newLabel.trim()}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white transition-colors"
              >
                <Save size={14} />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}

          {/* Saved loops list */}
          {loopMarkers.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Saved Loops
              </p>
              <div className="space-y-1">
                {loopMarkers.map((m) => (
                  <div
                    key={m.id}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                      activeLoop?.id === m.id
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                        : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleActivateLoop(m)}
                        className={`p-1 rounded transition-colors ${
                          activeLoop?.id === m.id
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400'
                        }`}
                        title="Play this loop"
                      >
                        {activeLoop?.id === m.id ? <Repeat size={16} /> : <Play size={16} />}
                      </button>
                      <span className="font-medium text-gray-900 dark:text-white">{m.label}</span>
                      <span className="text-gray-500 dark:text-gray-400">
                        {formatTime(m.start_secs)} - {formatTime(m.end_secs)}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteLoop(m)}
                      className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors"
                      title="Delete loop"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
