import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, Eye, FileDown, FileSpreadsheet, Loader2, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import { listAnalyses, deleteAnalysis, type AnalysisReport } from '../api/analysis'
import { downloadPDF, downloadExcel } from '../api/reports'
import PlatformBadge from '../components/PlatformBadge'
import { format } from 'date-fns'
import toast from 'react-hot-toast'

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  pending: 'bg-gray-100 text-gray-600',
  parsing: 'bg-blue-100 text-blue-700',
  analyzing: 'bg-purple-100 text-purple-700',
}

export default function History() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPlatform, setFilterPlatform] = useState('')
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['analyses', page, filterStatus, filterPlatform],
    queryFn: () => listAnalyses(page, 15),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAnalysis,
    onSuccess: () => {
      toast.success('Analysis deleted')
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
      setDeleteId(null)
    },
    onError: () => toast.error('Delete failed'),
  })

  const items = (data?.items ?? []).filter(a => {
    if (search && !a.id.includes(search) && !a.platform.includes(search.toLowerCase())) return false
    if (filterStatus && a.status !== filterStatus) return false
    if (filterPlatform && a.platform !== filterPlatform) return false
    return true
  })

  const totalPages = data?.pages ?? 1

  const handleDownload = async (id: string, type: 'pdf' | 'excel') => {
    try {
      if (type === 'pdf') await downloadPDF(id)
      else await downloadExcel(id)
    } catch { toast.error('Download failed') }
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Analysis History</h2>
        <p className="text-sm text-gray-500 mt-0.5">All past root cause analyses</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="input pl-8"
            placeholder="Search by ID or platform..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-auto" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
        </select>
        <select className="input w-auto" value={filterPlatform} onChange={e => setFilterPlatform(e.target.value)}>
          <option value="">All platforms</option>
          <option value="uipath">UiPath</option>
          <option value="power_automate">Power Automate</option>
          <option value="blue_prism">Blue Prism</option>
          <option value="automation_anywhere">Automation Anywhere</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['Analysis ID', 'Platform', 'Status', 'Confidence', 'Root Causes', 'Date', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center"><Loader2 size={20} className="animate-spin mx-auto text-gray-400" /></td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400 text-sm">No analyses found</td></tr>
              ) : (
                items.map(a => {
                  const primaryCause = a.root_causes?.causes?.[0]
                  return (
                    <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-gray-600 whitespace-nowrap">{a.id.slice(0, 12)}…</td>
                      <td className="px-4 py-3"><PlatformBadge platform={a.platform} size="sm" /></td>
                      <td className="px-4 py-3">
                        <span className={`badge ${STATUS_STYLES[a.status] || 'bg-gray-100 text-gray-600'}`}>{a.status}</span>
                      </td>
                      <td className="px-4 py-3">
                        {a.overall_confidence != null ? (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary-500 rounded-full"
                                style={{ width: `${Math.round(a.overall_confidence * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-600">{Math.round(a.overall_confidence * 100)}%</span>
                          </div>
                        ) : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-700">
                        {primaryCause ? (
                          <span>{primaryCause.title.slice(0, 30)}{primaryCause.title.length > 30 ? '…' : ''}</span>
                        ) : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {format(new Date(a.created_at), 'MMM d, yy HH:mm')}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {a.status === 'completed' && (
                            <button onClick={() => navigate(`/analysis/${a.id}/results`)} className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded" title="View results">
                              <Eye size={14} />
                            </button>
                          )}
                          {['pending','parsing','analyzing'].includes(a.status) && (
                            <button onClick={() => navigate(`/analysis/${a.id}/progress`)} className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded" title="View progress">
                              <Loader2 size={14} className="animate-spin" />
                            </button>
                          )}
                          {a.status === 'completed' && (
                            <>
                              <button onClick={() => handleDownload(a.id, 'pdf')} className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded" title="Download PDF">
                                <FileDown size={14} />
                              </button>
                              <button onClick={() => handleDownload(a.id, 'excel')} className="p-1.5 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded" title="Download Excel">
                                <FileSpreadsheet size={14} />
                              </button>
                            </>
                          )}
                          <button onClick={() => setDeleteId(a.id)} className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded" title="Delete">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-500">
              Page {page} of {totalPages} · {data?.total ?? 0} total
            </p>
            <div className="flex gap-1">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary p-1.5 disabled:opacity-40">
                <ChevronLeft size={14} />
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="btn-secondary p-1.5 disabled:opacity-40">
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete confirmation modal */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <AlertCircle size={18} className="text-red-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Delete Analysis?</h3>
                <p className="text-xs text-gray-500">This action cannot be undone.</p>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button
                onClick={() => deleteMutation.mutate(deleteId)}
                disabled={deleteMutation.isPending}
                className="btn-danger flex-1 justify-center"
              >
                {deleteMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
