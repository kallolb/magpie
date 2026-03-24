import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Home,
  Grid3x3,
  Download,
  Search,
  Scissors,
  BarChart3,
  Settings,
  ChevronDown,
  X,
} from 'lucide-react'
import { useAppStore } from '@/store'
import { Category, DownloadStatus } from '@/types'

interface SidebarProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function Sidebar({ open, onOpenChange }: SidebarProps) {
  const location = useLocation()
  const { categories, fetchCategories, activeDownloads } = useAppStore()
  const [categoriesExpanded, setCategoriesExpanded] = useState(true)
  const [downloadsExpanded, setDownloadsExpanded] = useState(true)

  useEffect(() => {
    fetchCategories()
  }, [fetchCategories])

  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { label: 'Dashboard', path: '/', icon: Home },
    { label: 'Browse', path: '/browse', icon: Grid3x3 },
    { label: 'Download', path: '/download', icon: Download },
    { label: 'Search', path: '/search', icon: Search },
    { label: 'Compilations', path: '/compilations', icon: Scissors },
    { label: 'Analytics', path: '/analytics', icon: BarChart3 },
    { label: 'Settings', path: '/settings', icon: Settings },
  ]

  const downloads = Array.from(activeDownloads.values())

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => onOpenChange(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:relative w-64 h-screen bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-y-auto transition-transform z-40 ${
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="p-4">
          {/* Close button for mobile */}
          <div className="flex justify-between items-center mb-6 lg:hidden">
            <div className="flex items-center gap-2">
              <img src="/logo.jpg" alt="Magpie" className="w-8 h-8 rounded-full object-cover" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                Magpie
              </h1>
            </div>
            <button onClick={() => onOpenChange(false)}>
              <X size={24} className="text-gray-600 dark:text-gray-400" />
            </button>
          </div>

          {/* Logo for desktop */}
          <div className="hidden lg:flex items-center gap-3 mb-8">
            <img src="/logo.jpg" alt="Magpie" className="w-10 h-10 rounded-full object-cover" />
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white leading-tight">
                Magpie
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Video Collector
              </p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-2 mb-8">
            {navItems.map(({ label, path, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                onClick={() => onOpenChange(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive(path)
                    ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <Icon size={20} />
                <span className="text-sm font-medium">{label}</span>
              </Link>
            ))}
          </nav>

          {/* Categories Section */}
          <div className="mb-6">
            <button
              onClick={() => setCategoriesExpanded(!categoriesExpanded)}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <span>Categories</span>
              <ChevronDown
                size={16}
                className={`ml-auto transition-transform ${
                  categoriesExpanded ? '' : '-rotate-90'
                }`}
              />
            </button>

            {categoriesExpanded && (
              <div className="mt-2 space-y-1 pl-4">
                {categories.length === 0 ? (
                  <p className="text-xs text-gray-500 dark:text-gray-400 py-2">
                    No categories
                  </p>
                ) : (
                  categories.map((cat: Category) => (
                    <div
                      key={cat.name}
                      className="flex items-center justify-between px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <span>{cat.name}</span>
                      <span className="text-gray-400 dark:text-gray-500">
                        ({cat.video_count})
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Active Downloads Section */}
          {downloads.length > 0 && (
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                onClick={() => setDownloadsExpanded(!downloadsExpanded)}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <span>Downloads</span>
                <ChevronDown
                  size={16}
                  className={`ml-auto transition-transform ${
                    downloadsExpanded ? '' : '-rotate-90'
                  }`}
                />
              </button>

              {downloadsExpanded && (
                <div className="mt-2 space-y-2 pl-4">
                  {downloads.map((download: DownloadStatus) => (
                    <div key={download.id} className="space-y-1">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                        <span className="text-xs text-gray-600 dark:text-gray-400 truncate">
                          {download.video?.title || 'Downloading...'}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full transition-all"
                          style={{ width: `${download.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-500">
                        {download.progress}%
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
