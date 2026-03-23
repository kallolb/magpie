import { X } from 'lucide-react'
import { getTagColor } from '@/utils/colors'

interface TagBadgeProps {
  name: string
  onRemove?: () => void
  interactive?: boolean
}

export default function TagBadge({ name, onRemove, interactive = false }: TagBadgeProps) {
  const colorClass = getTagColor(name)

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {name}
      {interactive && onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 inline-flex items-center hover:opacity-75 transition-opacity"
        >
          <X size={14} />
        </button>
      )}
    </span>
  )
}
