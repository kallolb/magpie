import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid,
  AreaChart, Area,
} from 'recharts'
import { HardDrive, Video, Clock, Activity, Tag, Repeat } from 'lucide-react'
import { apiClient } from '@/api/client'

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#64748b']

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

function formatDuration(secs: number): string {
  if (secs < 60) return `${secs}s`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
}

function StatCard({ icon: Icon, label, value, sub }: { icon: any; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
          <Icon size={20} className="text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</p>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{value}</p>
          {sub && <p className="text-xs text-gray-500 dark:text-gray-400">{sub}</p>}
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-700 pb-2">
        {title}
      </h2>
      {children}
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{title}</h3>
      {children}
    </div>
  )
}

export default function Analytics() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiClient.getAnalytics()
      .then(setData)
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />)}
        </div>
        {[...Array(3)].map((_, i) => <div key={i} className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg" />)}
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
        <p className="text-red-700 dark:text-red-400">{error || 'No data available'}</p>
      </div>
    )
  }

  const { storage, collection, content, activity } = data
  const successRate = collection.download_success_rate.total > 0
    ? Math.round((collection.download_success_rate.completed / collection.download_success_rate.total) * 100)
    : 0

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={HardDrive} label="Total Storage" value={formatBytes(storage.total_bytes)} sub={`${storage.total_completed} videos`} />
        <StatCard icon={Video} label="Total Videos" value={String(collection.download_success_rate.total)} sub={`${successRate}% success rate`} />
        <StatCard icon={Clock} label="Avg Duration" value={formatDuration(content.avg_duration)} />
        <StatCard icon={Activity} label="Last 7 Days" value={String(activity.recent.last_7_days)} sub={`vs ${activity.recent.prior_7_days} prior week`} />
      </div>

      {/* Storage Analytics */}
      <Section title="Storage Analytics">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Storage by Category">
            {storage.by_category.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={storage.by_category} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" tickFormatter={(v) => formatBytes(v)} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 12 }} width={75} />
                  <Tooltip formatter={(v) => formatBytes(v as number)} />
                  <Bar dataKey="total_bytes" fill="#6366f1" radius={[0, 4, 4, 0]} name="Size" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          <ChartCard title="Storage by Platform">
            {storage.by_platform.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={storage.by_platform} dataKey="total_bytes" nameKey="platform" cx="50%" cy="50%" outerRadius={90} label={(props: any) => `${props.platform} ${(props.percent * 100).toFixed(0)}%`} labelLine={false}>
                    {storage.by_platform.map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatBytes(v as number)} />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          {storage.growth.length > 1 && (
            <ChartCard title="Storage Growth Over Time">
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={storage.growth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => formatBytes(v)} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => formatBytes(v as number)} />
                  <Area type="monotone" dataKey="cumulative_bytes" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} name="Cumulative" />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
          )}

          {storage.largest_videos.length > 0 && (
            <ChartCard title="Largest Videos">
              <div className="space-y-2 max-h-[250px] overflow-y-auto">
                {storage.largest_videos.map((v: any, i: number) => (
                  <div key={v.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-gray-400 w-5 text-right flex-shrink-0">{i + 1}.</span>
                      <span className="text-gray-900 dark:text-white truncate">{v.title}</span>
                    </div>
                    <span className="text-gray-500 dark:text-gray-400 flex-shrink-0 ml-2">{formatBytes(v.file_size_bytes)}</span>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>
      </Section>

      {/* Video Collection */}
      <Section title="Video Collection">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Videos by Platform">
            {collection.by_platform.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={collection.by_platform}>
                  <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Videos" />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          <ChartCard title="Videos by Category">
            {collection.by_category.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={collection.by_category} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={90} label={(props: any) => `${props.category} (${props.count})`} labelLine={false}>
                    {collection.by_category.map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          <ChartCard title="Download Status">
            {collection.by_status.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={collection.by_status}>
                  <XAxis dataKey="status" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]} name="Count">
                    {collection.by_status.map((entry: any, i: number) => (
                      <Cell key={i} fill={entry.status === 'completed' ? '#10b981' : entry.status === 'failed' ? '#ef4444' : '#f59e0b'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          {collection.top_uploaders.length > 0 && (
            <ChartCard title="Top Uploaders">
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {collection.top_uploaders.map((u: any, i: number) => (
                  <div key={u.uploader} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <span className="text-gray-400 w-5 text-right flex-shrink-0">{i + 1}.</span>
                      <span className="text-gray-900 dark:text-white truncate">{u.uploader}</span>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                      <span className="text-gray-500 dark:text-gray-400">{u.count} videos</span>
                      <span className="text-gray-400 dark:text-gray-500">{formatBytes(u.total_bytes)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          )}
        </div>
      </Section>

      {/* Content Analytics */}
      <Section title="Content Analytics">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Duration Distribution">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={content.duration_distribution}>
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} name="Videos" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="File Size Distribution">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={content.size_distribution}>
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} name="Videos" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Resolution Breakdown">
            {content.resolution_breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={content.resolution_breakdown} dataKey="count" nameKey="resolution" cx="50%" cy="50%" outerRadius={80} label={(props: any) => `${props.resolution} (${props.count})`} labelLine={false}>
                    {content.resolution_breakdown.map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-gray-500 dark:text-gray-400 py-8 text-center">No data yet</p>}
          </ChartCard>

          {content.top_tags.length > 0 && (
            <ChartCard title="Most Used Tags">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={content.top_tags} layout="vertical" margin={{ left: 60 }}>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={55} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} name="Videos" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}

          {content.avg_duration_by_platform.length > 0 && (
            <ChartCard title="Average Duration by Platform">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={content.avg_duration_by_platform}>
                  <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
                  <YAxis tickFormatter={(v) => formatDuration(v)} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => formatDuration(v as number)} />
                  <Bar dataKey="avg_duration" fill="#ec4899" radius={[4, 4, 0, 0]} name="Avg Duration" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      </Section>

      {/* Activity Analytics */}
      <Section title="Activity">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Tag} label="Total Tags" value={String(content.top_tags.reduce((sum: number, t: any) => sum + t.count, 0))} sub={`${content.top_tags.length} unique tags`} />
          <StatCard icon={Repeat} label="Loop Markers" value={String(activity.loop_markers.total_loops)} sub={`on ${activity.loop_markers.videos_with_loops} videos`} />
          <StatCard icon={Video} label="Platforms" value={String(collection.by_platform.length)} />
          <StatCard icon={Activity} label="Categories" value={String(collection.by_category.length)} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {activity.daily_downloads.length > 0 && (
            <ChartCard title="Downloads (Last 30 Days)">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={activity.daily_downloads}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis dataKey="day" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} name="Downloads" />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          )}

          {activity.by_day_of_week.length > 0 && (
            <ChartCard title="Downloads by Day of Week">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={activity.by_day_of_week}>
                  <XAxis dataKey="day_name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#14b8a6" radius={[4, 4, 0, 0]} name="Downloads" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      </Section>
    </div>
  )
}
