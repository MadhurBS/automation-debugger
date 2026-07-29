import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Activity, CheckCircle, XCircle, Clock, Upload, ArrowRight, FileText, Cpu } from 'lucide-react'
import { listAnalyses } from '../api/analysis'
import { listProjects } from '../api/projects'
import PlatformBadge from '../components/PlatformBadge'
import { format } from 'date-fns'
import clsx from 'clsx'

const PLATFORM_COLORS: Record<string, string> = {
  uipath:              '#ff6900',
  power_automate:      '#0f62fe',   // IBM Blue 60
  blue_prism:          '#8a3ffc',
  automation_anywhere: '#ff7eb6',
  unknown:             '#8d8d8d',   // Carbon Gray 50
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'text-red-700 bg-red-50',
  high:     'text-orange-700 bg-orange-50',
  medium:   'text-yellow-800 bg-yellow-50',
  low:      'text-green-700 bg-green-50',
}

const RPA_TOOL_COLORS: Record<string, string> = {
  'UiPath':                    '#ff6900',
  'Blue Prism':                '#8a3ffc',
  'Automation Anywhere':       '#ff7eb6',
  'Power Automate Desktop':    '#0f62fe',
  'Power Automate Cloud':      '#2563eb',
  'Unknown':                   '#8d8d8d',
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

  // has_log ratio
  const withLog    = items.filter(a => a.has_log).length
  const logRatioPct = total > 0 ? Math.round((withLog / total) * 100) : 0

  // Platform distribution
  const platformCounts: Record<string, number> = {}
  items.forEach(a => {
    const p = a.platform || 'unknown'
    platformCounts[p] = (platformCounts[p] || 0) + 1
  })
  const pieData = Object.entries(platformCounts).map(([name, value]) => ({ name, value }))

  // RPA tool distribution (from completed analyses that have rpa_tool)
  const rpaToolCounts: Record<string, number> = {}
  items.forEach(a => {
    const t = a.rpa_tool || (a.ai_narrative?.rpa_tool) || ''
    if (t) {
      rpaToolCounts[t] = (rpaToolCounts[t] || 0) + 1
    }
  })
  const rpaToolData = Object.entries(rpaToolCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)

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
        <h2 className="text-xl font-semibold text-carbon-100">Dashboard</h2>
        <p className="text-sm text-carbon-60 mt-0.5">Overview of your automation analysis activity</p>
      </div>

      {/* ── Stat tiles — Carbon style ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-carbon-20 border border-carbon-20">
        {[
          { label: 'Total Analyses', value: total,           icon: Activity,     color: 'text-ibm-blue60',  bg: 'bg-ibm-blue10'  },
          { label: 'Completed',      value: completed,       icon: CheckCircle,  color: 'text-green-700',   bg: 'bg-green-50'    },
          { label: 'Failed',         value: failed,          icon: XCircle,      color: 'text-red-700',     bg: 'bg-red-50'      },
          { label: 'Success Rate',   value: `${successRate}%`, icon: Clock,      color: 'text-purple-700',  bg: 'bg-purple-50'   },
        ].map(s => (
          <div key={s.label} className="bg-white p-5 flex items-center gap-4">
            <div className={`w-10 h-10 ${s.bg} flex items-center justify-center flex-shrink-0`}>
              <s.icon size={18} className={s.color} />
            </div>
            <div>
              <p className="text-2xl font-light text-carbon-100 leading-none">{s.value}</p>
              <p className="text-xs text-carbon-60 mt-1">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ── Log coverage + RPA tool row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Log coverage card */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={14} className="text-carbon-50" />
            <h3 className="text-sm font-semibold text-carbon-90">Log Coverage</h3>
          </div>
          <div className="flex items-end gap-3 mb-2">
            <p className="text-3xl font-light text-ibm-blue60">{logRatioPct}%</p>
            <p className="text-xs text-carbon-60 mb-1">of analyses included an execution log</p>
          </div>
          <div className="h-2 bg-carbon-10 overflow-hidden mb-2">
            <div
              className={clsx('h-full transition-all', logRatioPct >= 60 ? 'bg-green-500' : logRatioPct >= 30 ? 'bg-yellow-400' : 'bg-carbon-40')}
              style={{ width: `${logRatioPct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-carbon-50">
            <span>{withLog} with log (runtime analysis)</span>
            <span>{total - withLog} without log (static only)</span>
          </div>
          {logRatioPct < 60 && total > 0 && (
            <p className="text-xs text-amber-700 bg-amber-50 px-2 py-1 mt-2">
              Upload execution logs alongside projects for more accurate runtime diagnosis.
            </p>
          )}
        </div>

        {/* RPA Tool breakdown */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Cpu size={14} className="text-carbon-50" />
            <h3 className="text-sm font-semibold text-carbon-90">RPA Tool Breakdown</h3>
            <span className="text-2xs text-carbon-40 ml-1">(AI-identified)</span>
          </div>
          {rpaToolData.length > 0 ? (
            <div className="space-y-2">
              {rpaToolData.map(([tool, count]) => {
                const pct = Math.round((count / total) * 100)
                const color = RPA_TOOL_COLORS[tool] || '#8d8d8d'
                return (
                  <div key={tool} className="flex items-center gap-2">
                    <div className="w-20 text-xs text-carbon-70 font-medium truncate">{tool}</div>
                    <div className="flex-1 h-1.5 bg-carbon-10 overflow-hidden">
                      <div
                        className="h-full transition-all"
                        style={{ width: `${pct}%`, background: color }}
                      />
                    </div>
                    <span className="text-xs text-carbon-50 w-6 text-right">{count}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="h-20 flex items-center justify-center text-carbon-40 text-xs">
              No AI-identified tools yet — run analyses with an OpenAI key to see tool breakdown.
            </div>
          )}
        </div>
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Activity chart */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-carbon-90 mb-4">Analysis Activity — Last 7 Days</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={activityData}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0f62fe" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#0f62fe" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6f6f6f' }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#6f6f6f' }} axisLine={false} tickLine={false} width={24} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 0, border: '1px solid #e0e0e0' }} />
              <Area type="monotone" dataKey="count" stroke="#0f62fe" strokeWidth={2} fill="url(#colorCount)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Platform pie */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-carbon-90 mb-4">By Platform</h3>
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
            <div className="h-32 flex items-center justify-center text-carbon-50 text-sm">No data yet</div>
          )}
        </div>
      </div>

      {/* ── Quick actions — Carbon "Clickable tile" ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { title: 'Upload Project', desc: 'Analyze a UiPath, Power Automate, Blue Prism, or AA project', path: '/upload/project', icon: Upload },
          { title: 'Upload Logs',    desc: 'Upload execution logs for root cause analysis',               path: '/upload/log',     icon: Activity },
        ].map(action => (
          <button
            key={action.path}
            onClick={() => navigate(action.path)}
            className="card p-5 text-left hover:shadow-card-hover border-l-4 border-l-ibm-blue60 transition-shadow flex items-center justify-between group"
          >
            <div className="flex items-center gap-4">
              <div className="w-9 h-9 bg-ibm-blue10 flex items-center justify-center">
                <action.icon size={16} className="text-ibm-blue60" />
              </div>
              <div>
                <p className="text-sm font-semibold text-carbon-100">{action.title}</p>
                <p className="text-xs text-carbon-60 mt-0.5">{action.desc}</p>
              </div>
            </div>
            <ArrowRight size={16} className="text-carbon-40 group-hover:text-ibm-blue60 transition-colors" />
          </button>
        ))}
      </div>

      {/* ── Recent analyses table ── */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-carbon-20">
          <h3 className="text-sm font-semibold text-carbon-90">Recent Analyses</h3>
          <button onClick={() => navigate('/history')} className="text-xs text-ibm-blue60 hover:underline">
            View all
          </button>
        </div>
        {recentItems.length === 0 ? (
          <div className="py-12 text-center text-carbon-50 text-sm">
            No analyses yet — upload a project to get started.
          </div>
        ) : (
          <div className="divide-y divide-carbon-10">
            {recentItems.map(a => {
              const topCause = a.root_causes?.causes?.[0]
              return (
                <div key={a.id} className="flex items-center gap-3 px-5 py-3 hover:bg-carbon-10 cursor-pointer" onClick={() => {
                  if (a.status === 'completed') navigate(`/analysis/${a.id}/results`)
                  else if (['pending','parsing','analyzing'].includes(a.status)) navigate(`/analysis/${a.id}/progress`)
                }}>
                  <PlatformBadge platform={a.platform} size="sm" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-carbon-100 truncate">{topCause?.title || 'Analysis #' + a.id.slice(0, 8)}</p>
                    <p className="text-xs text-carbon-60">{format(new Date(a.created_at), 'MMM d, yyyy HH:mm')}</p>
                  </div>
                  {a.has_log && (
                    <span className="badge bg-green-50 text-green-700 text-2xs">Log</span>
                  )}
                  {topCause && (
                    <span className={`badge ${SEVERITY_COLOR[topCause.severity] || 'bg-carbon-20 text-carbon-70'}`}>
                      {topCause.severity}
                    </span>
                  )}
                  <span className={`badge ${
                    a.status === 'completed' ? 'bg-green-100 text-green-800' :
                    a.status === 'failed'    ? 'bg-red-100 text-red-800' :
                                              'bg-ibm-blue10 text-ibm-blue70'
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
