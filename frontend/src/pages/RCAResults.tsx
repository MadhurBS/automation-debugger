import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle, CheckCircle, ArrowLeft, Loader2, FileDown, FileSpreadsheet,
  ShieldAlert, Code2, ListChecks, Bug, ChevronRight, Info,
} from 'lucide-react'
import { getAnalysisResult } from '../api/analysis'
import { type StandardsViolation, type CodeError } from '../api/analysis'
import { downloadPDF, downloadExcel } from '../api/reports'
import ConfidenceGauge from '../components/ConfidenceGauge'
import ExceptionTimeline from '../components/ExceptionTimeline'
import PlatformBadge from '../components/PlatformBadge'
import toast from 'react-hot-toast'
import { useState } from 'react'
import clsx from 'clsx'

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high:     'bg-orange-100 text-orange-800 border-orange-200',
  medium:   'bg-yellow-100 text-yellow-800 border-yellow-200',
  low:      'bg-green-100 text-green-800 border-green-200',
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-500',
  medium:   'bg-yellow-500',
  low:      'bg-green-500',
}

const SEV_TEXT: Record<string, string> = {
  critical: 'text-red-600', high: 'text-orange-600', medium: 'text-yellow-600', low: 'text-green-600',
}

type Tab = 'rca' | 'standards' | 'code-errors'

export default function RCAResults() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState<'pdf' | 'excel' | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('rca')

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['analysis-result', id],
    queryFn: () => getAnalysisResult(id!),
    enabled: !!id,
  })

  const handleDownload = async (type: 'pdf' | 'excel') => {
    if (!id) return
    setDownloading(type)
    try {
      if (type === 'pdf') await downloadPDF(id)
      else await downloadExcel(id)
      toast.success(`${type.toUpperCase()} downloaded`)
    } catch {
      toast.error('Download failed')
    } finally {
      setDownloading(null)
    }
  }

  if (isLoading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 size={28} className="animate-spin text-primary-500" />
    </div>
  )

  if (error || !report) return (
    <div className="card p-8 text-center">
      <AlertCircle size={32} className="mx-auto text-red-500 mb-3" />
      <p className="text-gray-700">Could not load analysis results.</p>
      <button onClick={() => navigate('/history')} className="btn-secondary mt-4">Back to History</button>
    </div>
  )

  const rootCauses    = report.root_causes?.causes ?? []
  const recommendations = report.recommendations?.items ?? []
  const violations    = report.standards_violations?.violations ?? []
  const codeErrors    = report.code_errors?.errors ?? []
  const primaryCause  = rootCauses[0]

  const stdScore = report.standards_score ?? null
  const criticalViolations = violations.filter(v => v.severity === 'critical').length
  const highViolations     = violations.filter(v => v.severity === 'high').length

  const tabs: { id: Tab; label: string; icon: typeof Bug; count?: number; countColor?: string }[] = [
    { id: 'rca',         label: 'Root Cause Analysis', icon: Bug,        count: rootCauses.length },
    { id: 'standards',   label: 'Coding Standards',    icon: ShieldAlert, count: violations.length, countColor: criticalViolations > 0 ? 'bg-red-500' : highViolations > 0 ? 'bg-orange-500' : 'bg-gray-400' },
    { id: 'code-errors', label: 'Code Errors',         icon: Code2,       count: codeErrors.length, countColor: codeErrors.length > 0 ? 'bg-orange-500' : 'bg-gray-400' },
  ]

  return (
    <div className="space-y-5 max-w-4xl">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button onClick={() => navigate('/history')} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-2">
            <ArrowLeft size={14} /> Back to History
          </button>
          <h2 className="text-xl font-bold text-gray-900">Analysis Results</h2>
          <div className="flex items-center gap-3 mt-1">
            <PlatformBadge platform={report.platform} size="sm" />
            <span className="badge bg-green-100 text-green-700">
              <CheckCircle size={11} className="mr-1" /> Completed
            </span>
            {report.ai_used && <span className="badge bg-purple-100 text-purple-700">AI-Powered</span>}
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={() => handleDownload('pdf')} disabled={downloading === 'pdf'} className="btn-secondary">
            {downloading === 'pdf' ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />}
            PDF
          </button>
          <button onClick={() => handleDownload('excel')} disabled={downloading === 'excel'} className="btn-secondary">
            {downloading === 'excel' ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />}
            Excel
          </button>
        </div>
      </div>

      {/* ── Summary scorecards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="card p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{rootCauses.length}</p>
          <p className="text-xs text-gray-500 mt-0.5">Root Causes</p>
        </div>
        <div className="card p-4 text-center">
          <p className={`text-2xl font-bold ${primaryCause ? SEV_TEXT[primaryCause.severity] ?? 'text-gray-900' : 'text-gray-400'}`}>
            {primaryCause?.severity?.toUpperCase() || 'N/A'}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">Top Severity</p>
        </div>
        <div className="card p-4 text-center">
          <p className={`text-2xl font-bold ${violations.length > 0 ? 'text-orange-600' : 'text-green-600'}`}>
            {violations.length}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">Std. Violations</p>
        </div>
        <div className="card p-4 text-center">
          <p className={`text-2xl font-bold ${codeErrors.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {codeErrors.length}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">Code Errors</p>
        </div>
        <div className="card p-4 flex flex-col items-center justify-center">
          <ConfidenceGauge value={Math.round((report.overall_confidence ?? 0) * 100)} size={76} />
        </div>
      </div>

      {/* Standards score bar */}
      {stdScore !== null && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <ListChecks size={15} className="text-gray-500" />
              <span className="text-sm font-semibold text-gray-900">Coding Standards Score</span>
            </div>
            <span className={clsx('text-lg font-bold', stdScore >= 80 ? 'text-green-600' : stdScore >= 50 ? 'text-yellow-600' : 'text-red-600')}>
              {stdScore}/100
            </span>
          </div>
          <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full transition-all', stdScore >= 80 ? 'bg-green-500' : stdScore >= 50 ? 'bg-yellow-500' : 'bg-red-500')}
              style={{ width: `${stdScore}%` }}
            />
          </div>
          {report.standards_violations?.summary && (
            <p className="text-xs text-gray-500 mt-2">{report.standards_violations.summary}</p>
          )}
        </div>
      )}

      {/* ── Tabs ───────────────────────────────────────────────────────────── */}
      <div className="flex border-b border-gray-200 gap-1">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === tab.id
                ? 'border-primary-600 text-primary-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            )}
          >
            <tab.icon size={14} />
            {tab.label}
            {tab.count !== undefined && (
              <span className={clsx('text-xs font-bold text-white rounded-full px-1.5 py-0.5 min-w-[20px] text-center', tab.countColor ?? 'bg-gray-400')}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════ TAB: RCA ══════════════════════════════════ */}
      {activeTab === 'rca' && (
        <div className="space-y-4">
          {rootCauses.length === 0 ? (
            <div className="card p-8 text-center text-gray-500 text-sm">No root causes identified</div>
          ) : (
            rootCauses.map((rc, i) => (
              <div key={i} className={`card border ${SEVERITY_STYLES[rc.severity] || 'border-gray-200'}`}>
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`badge border ${SEVERITY_STYLES[rc.severity]}`}>{rc.severity.toUpperCase()}</span>
                        <span className="badge bg-gray-100 text-gray-600">{rc.category}</span>
                      </div>
                      <h4 className="text-base font-semibold text-gray-900">#{i + 1} {rc.title}</h4>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-2xl font-bold text-gray-900">{Math.round(rc.confidence * 100)}%</p>
                      <p className="text-xs text-gray-500">confidence</p>
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 leading-relaxed mb-4">{rc.description}</p>

                  {(rc.affected_workflow || rc.affected_activity) && (
                    <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
                      {rc.affected_workflow && <span>📂 <strong>Workflow:</strong> {rc.affected_workflow}</span>}
                      {rc.affected_activity && <span>🔧 <strong>Activity:</strong> {rc.affected_activity}</span>}
                    </div>
                  )}

                  {rc.evidence.length > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Evidence</p>
                      <div className="space-y-1">
                        {rc.evidence.slice(0, 4).map((ev, j) => (
                          <p key={j} className="text-xs font-mono bg-gray-900 text-gray-100 px-3 py-1.5 rounded">{ev}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {rc.suggested_fix && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                      <p className="text-xs font-semibold text-blue-800 mb-1">💡 Suggested Fix</p>
                      <p className="text-sm text-blue-900">{rc.suggested_fix}</p>
                    </div>
                  )}

                  {rc.preventive_recommendations.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Preventive Recommendations</p>
                      <ul className="space-y-1">
                        {rc.preventive_recommendations.map((r, j) => (
                          <li key={j} className="flex items-start gap-2 text-sm text-gray-700">
                            <CheckCircle size={13} className="text-green-500 mt-0.5 flex-shrink-0" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Timeline */}
          {rootCauses.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">Execution Timeline</h3>
              <ExceptionTimeline events={[
                { level: 'info', message: 'Process started', timestamp: '' },
                ...(primaryCause?.evidence?.slice(0, 3).map(ev => ({ level: 'error' as const, message: ev, timestamp: '' })) ?? []),
                { level: 'error', message: `Exception: ${primaryCause?.title || 'Failure'}`, timestamp: '' },
              ]} />
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4">All Recommendations & Action Items</h3>
              <ol className="space-y-2">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
                    <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
                    {rec}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {/* ════════════════════ TAB: CODING STANDARDS ═══════════════════════════ */}
      {activeTab === 'standards' && (
        <div className="space-y-4">
          {violations.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={36} className="mx-auto text-green-500 mb-3" />
              <p className="text-base font-semibold text-gray-900">All standards passed!</p>
              <p className="text-sm text-gray-500 mt-1">No coding standard violations were found in this project.</p>
            </div>
          ) : (
            <>
              {/* Group by severity */}
              {(['critical', 'high', 'medium', 'low'] as const).map(sev => {
                const sevViolations = violations.filter((v: StandardsViolation) => v.severity === sev)
                if (sevViolations.length === 0) return null
                return (
                  <div key={sev}>
                    <h3 className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">
                      <span className={clsx('w-2.5 h-2.5 rounded-full', SEVERITY_DOT[sev])} />
                      {sev} ({sevViolations.length})
                    </h3>
                    <div className="space-y-2">
                      {sevViolations.map((v: StandardsViolation, i: number) => (
                        <div key={i} className={`card border ${SEVERITY_STYLES[sev]} p-0 overflow-hidden`}>
                          <div className="p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-mono text-xs font-bold text-gray-500">{v.rule_id}</span>
                                  <span className={`badge border text-xs ${SEVERITY_STYLES[sev]}`}>{sev.toUpperCase()}</span>
                                </div>
                                <p className="text-sm font-semibold text-gray-900">{v.rule_name}</p>
                                <p className="text-xs text-gray-600 mt-1">{v.description}</p>
                              </div>
                              <ChevronRight size={16} className="text-gray-400 flex-shrink-0 mt-1" />
                            </div>

                            {/* Location */}
                            <div className="flex items-center gap-1.5 mt-3 text-xs text-gray-500">
                              <Code2 size={11} />
                              <span className="font-medium">Location:</span>
                              <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">{v.location}</span>
                              <span className="text-gray-400">({v.location_type})</span>
                            </div>

                            {/* Recommendation */}
                            <div className="mt-3 bg-white/60 rounded-lg p-3 border border-current/10">
                              <p className="text-xs font-semibold text-gray-700 mb-1 flex items-center gap-1">
                                <Info size={11} /> Recommendation
                              </p>
                              <p className="text-xs text-gray-700">{v.recommendation}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}

              {/* Passed rules */}
              {(report.standards_violations?.passed_rules?.length ?? 0) > 0 && (
                <div className="card p-4">
                  <p className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1.5">
                    <CheckCircle size={13} /> Passed Rules ({report.standards_violations!.passed_rules.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {report.standards_violations!.passed_rules.map((r, i) => (
                      <span key={i} className="font-mono text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded">
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ════════════════════ TAB: CODE ERRORS ════════════════════════════════ */}
      {activeTab === 'code-errors' && (
        <div className="space-y-4">
          {codeErrors.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={36} className="mx-auto text-green-500 mb-3" />
              <p className="text-base font-semibold text-gray-900">No code errors detected</p>
              <p className="text-sm text-gray-500 mt-1">Static analysis found no errors in the parsed project structure.</p>
            </div>
          ) : (
            codeErrors.map((ce: CodeError, i: number) => (
              <div key={i} className={`card border ${SEVERITY_STYLES[ce.severity] || 'border-gray-200'}`}>
                <div className="p-5">
                  <div className="flex items-start gap-3 mb-3">
                    <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', SEVERITY_STYLES[ce.severity])}>
                      <Bug size={15} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`badge border ${SEVERITY_STYLES[ce.severity]}`}>{ce.severity.toUpperCase()}</span>
                        <span className="font-mono text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{ce.error_type}</span>
                      </div>
                      <h4 className="text-sm font-semibold text-gray-900">{ce.title}</h4>
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 leading-relaxed mb-3">{ce.description}</p>

                  {/* Location + line hint */}
                  <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
                    <div className="bg-gray-50 rounded-lg p-2.5">
                      <p className="font-semibold text-gray-500 mb-0.5">Location</p>
                      <p className="font-mono text-gray-800">{ce.location}</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-2.5">
                      <p className="font-semibold text-gray-500 mb-0.5">Activity / Stage</p>
                      <p className="font-mono text-gray-800">{ce.line_hint || '—'}</p>
                    </div>
                  </div>

                  {/* Fix */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-blue-800 mb-1">🔧 How to Fix</p>
                    <p className="text-sm text-blue-900">{ce.fix}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
