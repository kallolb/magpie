import { useCallback } from 'react'
import { useAppStore } from '@/store'
import { apiClient } from '@/api/client'
import { Tag } from '@/types'

export const useTags = () => {
  const { tags, tagsLoading, fetchTags } = useAppStore()

  const addTag = useCallback(
    async (name: string): Promise<Tag> => {
      const tag = await apiClient.createTag(name)
      await fetchTags()
      return tag
    },
    [fetchTags]
  )

  const removeTag = useCallback(
    async (id: number) => {
      await apiClient.deleteTag(id)
      await fetchTags()
    },
    [fetchTags]
  )

  const loadTags = useCallback(() => {
    return fetchTags()
  }, [fetchTags])

  return {
    tags,
    loading: tagsLoading,
    addTag,
    removeTag,
    loadTags,
  }
}
