import { useEffect, useCallback } from 'react'
import { useAppStore } from '@/store'

const DEBOUNCE_DELAY = 300

export const useSearch = () => {
  const { searchQuery, searchResults, searchTotal, searchLoading, fetchSearchResults } =
    useAppStore()

  useEffect(() => {
    if (!searchQuery.trim()) {
      return
    }

    const timer = setTimeout(() => {
      fetchSearchResults(searchQuery)
    }, DEBOUNCE_DELAY)

    return () => clearTimeout(timer)
  }, [searchQuery, fetchSearchResults])

  const setSearchQuery = useCallback(
    (query: string) => {
      useAppStore.setState({ searchQuery: query })
    },
    []
  )

  const clearSearch = useCallback(() => {
    useAppStore.setState({ searchQuery: '', searchResults: [], searchTotal: 0 })
  }, [])

  return {
    query: searchQuery,
    results: searchResults,
    total: searchTotal,
    loading: searchLoading,
    setQuery: setSearchQuery,
    clear: clearSearch,
  }
}
