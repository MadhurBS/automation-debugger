import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Activity, CheckCircle, XCircle, Clock, Upload, ArrowRight } from 'lucide-react'
import { listAnalyses } from '../api/analysis'
import { listProjects } from '../api/projects'
import PlatformBadge from '../components/PlatformBadge'
import { format } from 'date-fns'

const PLATFORM_COLORS: Record<string, string> = {
  uipath: '#ff6900',
  power_automate: '#0066ff',
  blue_prism: '#6d28d9',
  automation_anywhere: '#e91e8c',
  unknown: '#94a3b8',
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'text-red-600 bg-red-50',
  high: 'text-orange-600 bg-orange-50',
  medium: 'text-yellow-700 bg-yellow-50',
  low: 'text-green-700 bg-green-50',
}

export default function Dashboard() {
  const navigate = useNavigate()

  const { data: analyses } = useQuery({
    queryKey: ['analyses', 'dashboard'],
    queryFn: () => listAnalyses(1, 50),
  })

  const { data: projects } = useQuery({
    queryKey: ['projects', 'dashboard'],
    queryFn: () => listProjects(1, 50),
  })

  const items = analyses?.items ?? []
  const total = items.length
  const completed = items.filter(a => a.status === 'completed').length
  const failed = items.filter(a => a.status === 'failed').length
  const pending = items.filter(a => ['pending', 'parsing', 'analyzing'].includes(a.status)).length
  const successRate = total > 0 ? Math.round((completed / total) * 100) : 0

  // Platform distribution
  const platformCounts: Record<string, number> = {}
  items.forEach(a => {
    const p = a.platform || 'unknown'
    platformCounts[p] = (platformCounts[p] || 0) + 1
  })
  const pieData = Object.entries(platformCounts).map(([name, value]) => ({ name, value }))

  // Activity over last 7 days
  const now = new Date()
  const activityData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now)
    d.setDate(d.getDate() - (6 - i))
    const dateStr = format(d, 'MMM d')
    const count = items.filter(a => {
      const created = new Date(a.created_at)
      return format(created, 'MMM d') === dateStr
    }).length
    return { date: dateStr, count }
  })

  const recentItems = [...items].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 8)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-0.5">Overview of your automation analysis activity</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Analyses', value: total, icon: Activity, color: 'text-blue-600', bg: 'bg-blue-50' },
          { label: 'Completed', value: completed, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
          { label: 'Failed', value: failed, icon: XCircle, color: 'text-red-600', bg: 'bg-red-50' },
          { label: 'Success Rate', value: `${successRate}%`, icon: Clock, color: 'text-purple-600', bg: 'bg-purple-50' },
        ].map(s => (
          <div key={s.label} className="card p-4 flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg ${s.bg} flex items-center justify-center flex-shrink-0`}>
              <s.icon size={18} className={s.color} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-500">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Activity chart */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Analysis Activity (Last 7 Days)</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={activityData}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={24} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Area type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} fill="url(#colorCount)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Platform pie */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">By Platform</h3>
          {pieData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={140}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value" paddingAngle={2}>
                    {pieData.map(entry => (
                      <Cell key={entry.name} fill={PLATFORM_COLORS[entry.name] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {pieData.map(e => (
                  <div key={e.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: PLATFORM_COLORS[e.name] }} />
                      <PlatformBadge platform={e.name} size="sm" />
                    </div>
                    <span className="text-xs font-medium text-gray-700">{e.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-32 flex items-center justify-center text-gray-400 text-sm">No data yet</div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { title: 'Upload Project', desc: 'Analyze a UiPath, Power Automate, Blue Prism, or AA project', path: '/upload/project', icon: Upload },
          { title: 'Upload Logs', desc: 'Upload execution logs for root cause analysis', path: '/upload/log', icon: Activity },
        ].map(action => (
          <button
            key={action.path}
            onClick={() => navigate(action.path)}
            className="card p-5 text-left hover:shadow-card-hover transition-shadow flex items-center justify-between group"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-primary-50 rounded-lg flex items-center justify-center">
                <action.icon size={16} className="text-primary-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">{action.title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{action.desc}</p>
              </div>
            </div>
            <ArrowRight size={16} className="text-gray-400 group-hover:text-primary-600 transition-colors" />
          </button>
        ))}
      </div>

      {/* Recent analyses */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900">Recent Analyses</h3>
          <button onClick={() => navigate('/history')} className="text-xs text-primary-600 hover:underline">
            View all
          </button>
        </div>
        {recentItems.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            No analyses yet. Upload a project to get started.
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {recentItems.map(a => {
              const topCause = a.root_causes?.causes?.[0]
              return (
                <div key={a.id} className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 cursor-pointer" onClick={() => {
                  if (a.status === 'completed') navigate(`/analysis/${a.id}/results`)
                  else if (['pending','parsing','analyzing'].includes(a.status)) navigate(`/analysis/${a.id}/progress`)
                }}>
                  <PlatformBadge platform={a.platform} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{topCause?.title || 'Analysis #' + a.id.slice(0, 8)}</p>
                    <p className="text-xs text-gray-500">{format(new Date(a.created_at), 'MMM d, yyyy HH:mm')}</p>
                  </div>
                  {topCause && (
                    <span className={`badge text-xs ${SEVERITY_COLOR[topCause.severity] || 'bg-gray-100 text-gray-600'}`}>
                      {topCause.severity}
                    </span>
                  )}
                  <span className={`badge ${
                    a.status === 'completed' ? 'bg-green-100 text-green-700' :
                    a.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>{a.status}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
