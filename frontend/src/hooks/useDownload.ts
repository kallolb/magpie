import { useState, useCallback } from 'react'
import { DownloadRequest, DownloadStatus } from '@/types'
import { apiClient } from '@/api/client'
import { useAppStore } from '@/store'

interface UseDownloadReturn {
  submit: (request: DownloadRequest) => Promise<string>
  isDownloading: boolean
  error: string | null
  currentProgress: number
}

export const useDownload = (): UseDownloadReturn => {
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentProgress, setCurrentProgress] = useState(0)
  const { addActiveDownload, updateActiveDownload, removeActiveDownload } =
    useAppStore()

  const submit = useCallback(
    async (request: DownloadRequest): Promise<string> => {
      setIsDownloading(true)
      setError(null)
      setCurrentProgress(0)

      try {
        // Submit download request
        const initialStatus = await apiClient.submitDownload(request)
        const downloadId = initialStatus.id

        // Add to active downloads
        addActiveDownload(downloadId, initialStatus)

        // Listen to SSE progress updates
        const eventSource = new EventSource(`/api/downloads/${downloadId}/progress`)

        eventSource.onmessage = (event) => {
          try {
            const status: DownloadStatus = JSON.parse(event.data)
            updateActiveDownload(downloadId, status)
            setCurrentProgress(status.progress)

            const terminal = ['completed', 'failed', 'duplicate']
            if (terminal.includes(status.status)) {
              eventSource.close()
              setIsDownloading(false)
              if (status.status === 'failed') {
                setError(status.error_message || 'Download failed')
              } else if (status.status === 'duplicate') {
                setError('This video has already been downloaded')
              }
              // Refresh video list
              useAppStore.getState().fetchVideos()
              setTimeout(() => {
                removeActiveDownload(downloadId)
              }, 5000)
            }
          } catch (e) {
            console.error('Error parsing download status:', e)
          }
        }

        eventSource.onerror = () => {
          eventSource.close()
          setIsDownloading(false)
          setError('Connection lost')
        }

        return downloadId
      } catch (err: any) {
        const errorMessage = err.response?.data?.detail || err.message || 'Download failed'
        setError(errorMessage)
        setIsDownloading(false)
        throw err
      }
    },
    [addActiveDownload, updateActiveDownload, removeActiveDownload]
  )

  return {
    submit,
    isDownloading,
    error,
    currentProgress,
  }
}
