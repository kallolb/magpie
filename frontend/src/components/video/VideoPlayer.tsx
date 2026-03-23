import { useRef, useState } from 'react'
import { apiClient } from '@/api/client'

interface VideoPlayerProps {
  videoId: string
  title?: string
  thumbnailUrl?: string
}

export default function VideoPlayer({
  videoId,
  title: _title,
  thumbnailUrl,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)

  const handleError = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget
    setError(
      `Error loading video: ${video.error?.message || 'Unknown error'}`
    )
  }

  return (
    <div className="w-full bg-black rounded-lg overflow-hidden">
      {error ? (
        <div className="aspect-video flex flex-col items-center justify-center bg-gray-900 text-white">
          <svg
            className="w-16 h-16 mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-lg font-medium">{error}</p>
        </div>
      ) : (
        <video
          ref={videoRef}
          className="w-full h-auto"
          controls
          poster={thumbnailUrl}
          onError={handleError}
        >
          <source src={apiClient.getVideoStreamUrl(videoId)} type="video/mp4" />
          Your browser does not support the video tag.
        </video>
      )}
    </div>
  )
}
