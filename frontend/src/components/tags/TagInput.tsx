import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import { useAppStore } from '@/store'
import TagBadge from './TagBadge'

export interface TagInputHandle {
  /** Commit any pending input text and return the final tags list. */
  flush: () => string[]
}

interface TagInputProps {
  value: string[]
  onChange: (tags: string[]) => void
}

const TagInput = forwardRef<TagInputHandle, TagInputProps>(({ value, onChange }, ref) => {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const { tags, fetchTags } = useAppStore()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchTags()
  }, [fetchTags])

  useEffect(() => {
    if (input.trim()) {
      const lowerInput = input.toLowerCase()
      const filtered = tags
        .map((t) => t.name)
        .filter(
          (name) =>
            name.toLowerCase().includes(lowerInput) && !value.includes(name)
        )
      setSuggestions(filtered)
      setShowSuggestions(true)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }, [input, tags, value])

  const addTags = (text: string, currentTags: string[]): string[] => {
    const newTags = text
      .split(/[,\s]+/)
      .map((t) => t.trim())
      .filter((t) => t && !currentTags.includes(t))
    return [...currentTags, ...newTags]
  }

  useImperativeHandle(ref, () => ({
    flush: () => {
      if (input.trim()) {
        const updated = addTags(input, value)
        onChange(updated)
        setInput('')
        return updated
      }
      return value
    },
  }))

  const handleAddTag = (tag: string) => {
    const trimmedTag = tag.trim()
    if (!trimmedTag) return
    if (value.includes(trimmedTag)) return

    onChange([...value, trimmedTag])
    setInput('')
    setShowSuggestions(false)
  }

  const handleRemoveTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag))
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    // If the user typed a comma or space, commit tags immediately
    if (val.endsWith(',') || val.endsWith(' ')) {
      const newTags = addTags(val, value)
      if (newTags.length > value.length) {
        onChange(newTags)
        setInput('')
        return
      }
    }
    setInput(val)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (suggestions.length > 0) {
        handleAddTag(suggestions[0])
      } else if (input.trim()) {
        const newTags = addTags(input, value)
        onChange(newTags)
        setInput('')
        setShowSuggestions(false)
      }
    } else if (e.key === 'Backspace' && !input && value.length > 0) {
      handleRemoveTag(value[value.length - 1])
    }
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-2 p-2 min-h-10 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-200 dark:focus-within:ring-indigo-900">
        {value.map((tag) => (
          <TagBadge
            key={tag}
            name={tag}
            onRemove={() => handleRemoveTag(tag)}
            interactive
          />
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => input && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
          placeholder={value.length === 0 ? 'Add tags...' : ''}
          className="flex-1 min-w-32 outline-none bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
        />
      </div>

      {/* Suggestions Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg z-10">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => handleAddTag(suggestion)}
              className="w-full text-left px-4 py-2 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 text-gray-900 dark:text-white first:rounded-t-lg last:rounded-b-lg transition-colors"
            >
              <span className="text-sm">{suggestion}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
})

export default TagInput
