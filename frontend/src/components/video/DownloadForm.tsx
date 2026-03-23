import { useState, useEffect } from 'react'
import { Download, Copy, AlertCircle } from 'lucide-react'
import { useDownload } from '@/hooks/useDownload'
import { useAppStore } from '@/store'
import { DownloadRequest } from '@/types'
import TagInput from '@/components/tags/TagInput'

const QUALITY_OPTIONS = [
  { value: 360, label: '360p' },
  { value: 480, label: '480p' },
  { value: 720, label: '720p' },
  { value: 1080, label: '1080p' },
  { value: 2160, label: '4K' },
  { value: 0, label: 'Best Available' },
]

export default function DownloadForm() {
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [quality, setQuality] = useState(0)
  const [platform, setPlatform] = useState<'youtube' | 'instagram' | 'other'>('other')
  const [validUrl, setValidUrl] = useState(false)

  const { submit, isDownloading, error, currentProgress } = useDownload()
  const { categories, fetchCategories } = useAppStore()

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  useEffect(() => {
    // Detect platform from URL
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      setPlatform('youtube')
      setValidUrl(true)
    } else if (url.includes('instagram.com')) {
      setPlatform('instagram')
      setValidUrl(true)
    } else {
      setValidUrl(/^https?:\/\//.test(url))
      setPlatform('other')
    }
  }, [url])

  const handlePaste = async () => {
    const text = await navigator.clipboard.readText()
    setUrl(text)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validUrl) return

    const request: DownloadRequest = {
      url,
      category: category || undefined,
      tags: selectedTags.length > 0 ? selectedTags : undefined,
      quality: quality !== 0 ? quality : undefined,
    }

    try {
      await submit(request)
      // Reset form
      setUrl('')
      setCategory('')
      setSelectedTags([])
      setQuality(0)
    } catch (err) {
      console.error('Download error:', err)
    }
  }

  const getPlatformColor = () => {
    if (platform === 'youtube') return 'border-red-400 bg-red-50 dark:bg-red-900/20'
    if (platform === 'instagram') return 'border-pink-400 bg-pink-50 dark:bg-pink-900/20'
    return 'border-gray-400 bg-gray-50 dark:bg-gray-900/20'
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8"
    >
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Download Video
      </h2>

      {/* Error Alert */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
          <AlertCircle size={20} className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900 dark:text-red-300">Error</h3>
            <p className="text-sm text-red-700 dark:text-red-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* URL Input */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Video URL *
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=... or https://instagram.com/p/..."
            className={`flex-1 px-4 py-3 rounded-lg border-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500 transition-colors ${
              url && !validUrl
                ? 'border-red-300 dark:border-red-600'
                : validUrl
                  ? getPlatformColor()
                  : 'border-gray-300 dark:border-gray-600'
            }`}
          />
          <button
            type="button"
            onClick={handlePaste}
            className="px-4 py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors flex items-center gap-2"
          >
            <Copy size={20} />
            <span className="hidden sm:inline text-sm font-medium">Paste</span>
          </button>
        </div>
        {url && !validUrl && (
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            Please enter a valid URL starting with http:// or https://
          </p>
        )}
      </div>

      {/* Platform Indicator */}
      {validUrl && (
        <div className="mb-6 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>Platform detected:</strong> {platform.charAt(0).toUpperCase() + platform.slice(1)}
          </p>
        </div>
      )}

      {/* Category */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500"
        >
          <option value="">Uncategorized</option>
          {categories.map((cat) => (
            <option key={cat.name} value={cat.name}>
              {cat.name} ({cat.video_count})
            </option>
          ))}
        </select>
      </div>

      {/* Tags */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Tags
        </label>
        <TagInput value={selectedTags} onChange={setSelectedTags} />
      </div>

      {/* Quality */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Quality
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {QUALITY_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setQuality(option.value)}
              className={`py-2 rounded-lg transition-colors font-medium text-sm ${
                quality === option.value
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Progress Bar */}
      {isDownloading && (
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
            <span>Downloading...</span>
            <span>{Math.round(currentProgress)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${currentProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!validUrl || isDownloading}
        className={`w-full py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition-colors ${
          validUrl && !isDownloading
            ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
            : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
        }`}
      >
        <Download size={20} />
        {isDownloading ? 'Downloading...' : 'Start Download'}
      </button>
    </form>
  )
}
