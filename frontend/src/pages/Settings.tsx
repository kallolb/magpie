import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Key } from 'lucide-react'
import StorageConfig from '@/components/settings/StorageConfig'
import CategoryManager from '@/components/settings/CategoryManager'
import TagManager from '@/components/tags/TagManager'

export default function Settings() {
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  useEffect(() => {
    const saved = localStorage.getItem('api_key')
    if (saved) {
      setApiKey(saved)
    }
  }, [])

  const handleSaveApiKey = () => {
    if (apiKey.trim()) {
      localStorage.setItem('api_key', apiKey)
      setSaveMessage('API key saved successfully')
      setTimeout(() => setSaveMessage(null), 3000)
    }
  }

  const handleResetApiKey = () => {
    setApiKey('changeme')
    localStorage.setItem('api_key', 'changeme')
    setSaveMessage('API key reset to default')
    setTimeout(() => setSaveMessage(null), 3000)
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3 mb-2">
          <SettingsIcon size={32} />
          Settings
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Configure your video downloader application
        </p>
      </div>

      {/* API Key Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Key size={24} />
          API Key Configuration
        </h2>

        {saveMessage && (
          <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-sm text-green-700 dark:text-green-400">{saveMessage}</p>
          </div>
        )}

        <div className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            The API key is used to authenticate requests to the backend server. Keep it secure.
          </p>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              API Key
            </label>
            <div className="flex gap-2">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {showApiKey ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSaveApiKey}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors"
            >
              Save API Key
            </button>
            <button
              onClick={handleResetApiKey}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Reset to Default
            </button>
          </div>
        </div>
      </div>

      {/* Storage Configuration */}
      <StorageConfig />

      {/* Categories */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Categories
        </h2>
        <CategoryManager />
      </div>

      {/* Tags */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          Tags
        </h2>
        <TagManager />
      </div>

      {/* App Info */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          App Information
        </h2>
        <div className="space-y-3">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Application Name</p>
            <p className="font-semibold text-gray-900 dark:text-white">
              Magpie
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Version</p>
            <p className="font-semibold text-gray-900 dark:text-white">1.0.0</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Environment</p>
            <p className="font-semibold text-gray-900 dark:text-white">
              {import.meta.env.MODE || 'production'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
