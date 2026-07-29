import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle, CheckCircle, ArrowLeft, Loader2, FileDown, FileSpreadsheet,
  ShieldAlert, Code2, Bug, Info, GitBranch, Package, Workflow,
  Activity, ShieldCheck, FileWarning, ChevronRight, ListChecks,
} from 'lucide-react'
import { getAnalysisResult } from '../api/analysis'
import { type StandardsViolation, type CodeError, type RuntimeAnalysis, type AINarrative, type AINarrativeCause } from '../api/analysis'
import { downloadPDF, downloadExcel } from '../api/reports'
import ConfidenceGauge from '../components/ConfidenceGauge'
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
  critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-green-500',
}
const SEV_TEXT: Record<string, string> = {
  critical: 'text-red-600', high: 'text-orange-600', medium: 'text-yellow-600', low: 'text-green-600',
}
const FAILURE_CAT_COLOR: Record<string, string> = {
  'Application Issue':  'bg-red-100 text-red-800',
  'Infrastructure':     'bg-orange-100 text-orange-800',
  'Business Data':      'bg-yellow-100 text-yellow-800',
  'Configuration':      'bg-blue-100 text-blue-800',
  'Credentials':        'bg-purple-100 text-purple-800',
  'Network':            'bg-indigo-100 text-indigo-800',
  'Package Dependency': 'bg-pink-100 text-pink-800',
  'Coding Logic':       'bg-amber-100 text-amber-800',
  'Permissions':        'bg-rose-100 text-rose-800',
  'Environment':        'bg-teal-100 text-teal-800',
  'None — Success':     'bg-green-100 text-green-800',
}

// 3 tabs only — no Runtime Analysis tab, no Log Correlation tab
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
      <Loader2 size={28} className="animate-spin text-ibm-blue60" />
    </div>
  )
  if (error || !report) return (
    <div className="card p-8 text-center">
      <AlertCircle size={32} className="mx-auto text-red-500 mb-3" />
      <p className="text-carbon-70">Could not load analysis results.</p>
      <button onClick={() => navigate('/history')} className="btn-secondary mt-4">Back to History</button>
    </div>
  )

  const rootCauses      = report.root_causes?.causes ?? []
  const recommendations = report.recommendations?.items ?? []
  const violations      = report.standards_violations?.violations ?? []
  const codeErrors      = report.code_errors?.errors ?? []
  const projectSummary  = report.project_summary ?? {}
  const runtimeAnalysis = report.runtime_analysis as RuntimeAnalysis | undefined
  const aiNarrative     = report.ai_narrative as AINarrative | undefined
  const rpaToolLabel    = report.rpa_tool || aiNarrative?.rpa_tool || ''
  const primaryCause    = rootCauses[0]

  // has_log: log was uploaded (regardless of whether it had errors)
  const hasLog = report.has_log ?? !!runtimeAnalysis?.has_log

  // isSuccess: log was uploaded but no exceptions found
  const hasExceptions = !!(runtimeAnalysis?.exception_type)
  const isSuccess = hasLog && !hasExceptions

  const stdScore           = report.standards_score ?? null
  const criticalViolations = violations.filter(v => v.severity === 'critical').length
  const highViolations     = violations.filter(v => v.severity === 'high').length
  const rcaCount           = rootCauses.filter(rc => rc.category !== 'ProjectInfo').length

  const tabs: { id: Tab; label: string; icon: typeof Bug; count?: number; countColor?: string }[] = [
    {
      id: 'rca', label: 'Root Cause Analysis', icon: Bug,
      count: isSuccess ? 0 : rcaCount,
      countColor: isSuccess ? 'bg-green-500' : rcaCount > 0 ? 'bg-red-500' : 'bg-carbon-40',
    },
    {
      id: 'standards', label: 'Coding Standards', icon: ShieldAlert,
      count: violations.length,
      countColor: criticalViolations > 0 ? 'bg-red-500' : highViolations > 0 ? 'bg-orange-500' : 'bg-carbon-40',
    },
    {
      id: 'code-errors', label: 'Code Errors', icon: Code2,
      count: codeErrors.length,
      countColor: codeErrors.length > 0 ? 'bg-orange-500' : 'bg-carbon-40',
    },
  ]

  return (
    <div className="space-y-5 max-w-5xl">

      {/* ── Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button onClick={() => navigate('/history')} className="flex items-center gap-1.5 text-sm text-carbon-60 hover:text-carbon-100 mb-2">
            <ArrowLeft size={14} /> Back to History
          </button>
          <h2 className="text-xl font-semibold text-carbon-100">Analysis Results</h2>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <PlatformBadge platform={report.platform} size="sm" />
            <span className="badge bg-green-100 text-green-700">
              <CheckCircle size={11} className="mr-1" /> Completed
            </span>
            {report.ai_used && <span className="badge bg-purple-100 text-purple-700">AI-Powered</span>}
            {hasLog
              ? <span className="badge bg-ibm-blue10 text-ibm-blue70">✓ Log Uploaded</span>
              : <span className="badge bg-carbon-10 text-carbon-60">No Log</span>
            }
            {rpaToolLabel && <span className="badge bg-carbon-10 text-carbon-70">{rpaToolLabel}</span>}
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

      {/* ── Project summary bar ── */}
      {projectSummary.name && (
        <div className="card p-4 border-l-4 border-l-ibm-blue60">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-2">
              <Workflow size={14} className="text-ibm-blue60" />
              <span className="text-xs text-carbon-60">Project</span>
              <span className="text-sm font-semibold text-carbon-100">{projectSummary.name}</span>
            </div>
            {(projectSummary.workflow_count ?? 0) > 0 && (
              <div className="flex items-center gap-1.5">
                <GitBranch size={13} className="text-carbon-50" />
                <span className="text-xs text-carbon-60">{projectSummary.workflow_count} workflow{projectSummary.workflow_count !== 1 ? 's' : ''}</span>
              </div>
            )}
            {(projectSummary.package_names?.length ?? 0) > 0 && (
              <div className="flex items-center gap-1.5">
                <Package size={13} className="text-carbon-50" />
                <span className="text-xs text-carbon-60">{projectSummary.package_names?.length} package{(projectSummary.package_names?.length ?? 1) !== 1 ? 's' : ''}</span>
              </div>
            )}
            {projectSummary.metadata?.version && (
              <span className="text-xs text-carbon-50">v{projectSummary.metadata.version}</span>
            )}
            {projectSummary.workflow_names?.slice(0, 3).map((wn: string) => (
              <span key={wn} className="font-mono text-2xs bg-carbon-10 text-carbon-70 px-2 py-0.5">{wn}</span>
            ))}
          </div>
        </div>
      )}

      {/* ── Scorecards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-carbon-20 border border-carbon-20">
        <div className="bg-white p-4 text-center">
          <p className={clsx('text-2xl font-light', isSuccess ? 'text-green-600' : rcaCount > 0 ? 'text-red-600' : 'text-carbon-100')}>
            {isSuccess ? '✓' : rcaCount}
          </p>
          <p className="text-xs text-carbon-60 mt-0.5">{isSuccess ? 'No Issues Found' : 'Root Causes'}</p>
        </div>
        <div className="bg-white p-4 text-center">
          <p className={clsx('text-2xl font-light', isSuccess ? 'text-green-600' : primaryCause ? SEV_TEXT[primaryCause.severity] ?? 'text-carbon-100' : 'text-carbon-40')}>
            {isSuccess ? 'SUCCESS' : primaryCause?.severity?.toUpperCase() || 'N/A'}
          </p>
          <p className="text-xs text-carbon-60 mt-0.5">Top Severity</p>
        </div>
        <div className="bg-white p-4 text-center">
          <p className={clsx('text-2xl font-light', violations.length > 0 ? 'text-orange-600' : 'text-green-600')}>
            {violations.length}
          </p>
          <p className="text-xs text-carbon-60 mt-0.5">Std. Violations</p>
        </div>
        <div className="bg-white p-4 flex flex-col items-center justify-center">
          <ConfidenceGauge value={Math.round((report.overall_confidence ?? 0) * 100)} size={76} />
        </div>
      </div>

      {/* Standards score bar */}
      {stdScore !== null && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <ListChecks size={15} className="text-carbon-50" />
              <span className="text-sm font-semibold text-carbon-90">Coding Standards Score</span>
            </div>
            <span className={clsx('text-lg font-semibold', stdScore >= 80 ? 'text-green-700' : stdScore >= 50 ? 'text-yellow-700' : 'text-red-700')}>
              {stdScore}/100
            </span>
          </div>
          <div className="h-2 bg-carbon-10 overflow-hidden">
            <div
              className={clsx('h-full transition-all', stdScore >= 80 ? 'bg-green-500' : stdScore >= 50 ? 'bg-yellow-500' : 'bg-red-500')}
              style={{ width: `${stdScore}%` }}
            />
          </div>
          {report.standards_violations?.summary && (
            <p className="text-xs text-carbon-60 mt-2">{report.standards_violations.summary}</p>
          )}
        </div>
      )}

      {/* ── 3 Tabs ── */}
      <div className="flex border-b border-carbon-20">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === tab.id
                ? 'border-ibm-blue60 text-ibm-blue60'
                : 'border-transparent text-carbon-60 hover:text-carbon-100'
            )}
          >
            <tab.icon size={14} />
            {tab.label}
            {tab.count !== undefined && (
              <span className={clsx('text-2xs font-bold text-white px-1.5 py-0.5 min-w-[20px] text-center', tab.countColor ?? 'bg-carbon-40')}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════ ROOT CAUSE ANALYSIS TAB ══════════════════════════════════ */}
      {activeTab === 'rca' && (
        <div className="space-y-5">

          {/* Log status banner */}
          {hasLog ? (
            isSuccess ? (
              <div className="flex items-center gap-3 px-4 py-3 bg-green-50 border border-green-200 text-sm text-green-800">
                <CheckCircle size={15} className="flex-shrink-0" />
                <div>
                  <strong>Log analysed — No errors found.</strong>
                  {' '}The uploaded log shows a successful run with no exceptions.
                  Any findings below are from static code review only.
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-3 px-4 py-3 bg-red-50 border border-red-200 text-sm text-red-800">
                <Activity size={15} className="flex-shrink-0" />
                <div>
                  <strong>Log analysed — Errors detected.</strong>
                  {' '}Root causes below are based on evidence extracted from the execution log.
                </div>
              </div>
            )
          ) : (
            <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 text-sm text-blue-800">
              <Info size={15} className="flex-shrink-0" />
              <div>
                <strong>No log file uploaded.</strong>
                {' '}Findings below are from static project analysis only.
                Upload an execution log for runtime-based diagnosis.
              </div>
            </div>
          )}

          {/* AI error summary */}
          {!isSuccess && aiNarrative?.runtime_error_summary && (
            <div className="flex items-start gap-3 px-4 py-3 bg-amber-50 border border-amber-200">
              <AlertCircle size={15} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-medium text-amber-900">{aiNarrative.runtime_error_summary}</p>
            </div>
          )}

          {/* Primary failure card — error runs with log */}
          {hasLog && !isSuccess && runtimeAnalysis?.exception_type && (
            <div className="card border-l-4 border-l-red-500 border border-carbon-20 p-5">
              <p className="text-2xs font-semibold text-carbon-50 uppercase tracking-widest mb-3">Primary Failure — from Log</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4 text-xs">
                <div className="bg-carbon-10 p-3">
                  <p className="font-semibold text-carbon-60 mb-1">Exception Type</p>
                  <p className="font-mono text-carbon-100">{runtimeAnalysis.exception_type}</p>
                </div>
                <div className="bg-carbon-10 p-3">
                  <p className="font-semibold text-carbon-60 mb-1">Failure Category</p>
                  <span className={clsx('badge', FAILURE_CAT_COLOR[runtimeAnalysis.failure_category] ?? 'bg-carbon-10 text-carbon-70')}>
                    {runtimeAnalysis.failure_category || '—'}
                  </span>
                </div>
                <div className="bg-carbon-10 p-3">
                  <p className="font-semibold text-carbon-60 mb-1">Error Message</p>
                  <p className="font-mono text-carbon-100 break-all">{runtimeAnalysis.error_message || '—'}</p>
                </div>
                <div className="bg-carbon-10 p-3">
                  <p className="font-semibold text-carbon-60 mb-1">Time of Failure</p>
                  <p className="font-mono text-carbon-100">{runtimeAnalysis.timestamp || '—'}</p>
                </div>
                {runtimeAnalysis.failed_workflow && (
                  <div className="bg-carbon-10 p-3 flex items-start gap-2">
                    <GitBranch size={12} className="text-ibm-blue60 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-carbon-60 mb-1">Failed Workflow</p>
                      <p className="font-mono text-carbon-100">{runtimeAnalysis.failed_workflow}</p>
                    </div>
                  </div>
                )}
                {runtimeAnalysis.failed_activity && (
                  <div className="bg-carbon-10 p-3 flex items-start gap-2">
                    <Code2 size={12} className="text-carbon-50 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-carbon-60 mb-1">Failed Activity / Stage</p>
                      <p className="font-mono text-carbon-100">{runtimeAnalysis.failed_activity}</p>
                    </div>
                  </div>
                )}
              </div>

              {runtimeAnalysis.root_cause_summary && (
                <div className="bg-amber-50 border border-amber-200 p-3 mb-4">
                  <p className="text-xs font-semibold text-amber-800 mb-1">What Happened</p>
                  <p className="text-sm text-amber-900">{runtimeAnalysis.root_cause_summary}</p>
                </div>
              )}

              {runtimeAnalysis.evidence_from_log.length > 0 && (
                <div className="mb-4">
                  <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">Evidence from Log</p>
                  <div className="space-y-1">
                    {runtimeAnalysis.evidence_from_log.map((ev, i) => (
                      <p key={i} className="text-xs font-mono bg-carbon-100 text-green-300 px-3 py-1.5 break-all whitespace-pre-wrap">{ev}</p>
                    ))}
                  </div>
                </div>
              )}

              {(runtimeAnalysis.all_exceptions?.length ?? 0) > 1 && (
                <div className="mb-4">
                  <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                    <FileWarning size={12} className="text-red-500" />
                    All Exceptions Found in Log ({runtimeAnalysis.all_exceptions.length})
                  </p>
                  <div className="space-y-1">
                    {runtimeAnalysis.all_exceptions.map((exc, i) => (
                      <div key={i} className="flex items-start gap-3 bg-carbon-10 px-3 py-2 text-xs">
                        <span className="badge bg-red-100 text-red-800 flex-shrink-0">{exc.type}</span>
                        <span className="font-mono text-carbon-80 break-all">{exc.message}</span>
                        {exc.timestamp && <span className="text-carbon-40 flex-shrink-0 ml-auto">{exc.timestamp}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {runtimeAnalysis.suggested_fixes.length > 0 && (
                <div className="mb-4">
                  <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">How to Fix</p>
                  <ul className="space-y-1.5">
                    {runtimeAnalysis.suggested_fixes.map((fix, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-carbon-70">
                        <ShieldCheck size={13} className="text-ibm-blue60 mt-0.5 flex-shrink-0" /> {fix}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {runtimeAnalysis.validation_steps.length > 0 && (
                <div>
                  <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">Validation Steps</p>
                  <ol className="space-y-1.5">
                    {runtimeAnalysis.validation_steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-carbon-70">
                        <span className="w-5 h-5 bg-ibm-blue10 text-ibm-blue70 text-xs font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* Success log summary card */}
          {hasLog && isSuccess && runtimeAnalysis && (
            <div className="card border-l-4 border-l-green-500 border border-carbon-20 p-5">
              <p className="text-2xs font-semibold text-carbon-50 uppercase tracking-widest mb-3">Log Analysis Summary</p>
              {runtimeAnalysis.evidence_from_log.length > 0 && (
                <div className="space-y-1 mb-3">
                  {runtimeAnalysis.evidence_from_log.map((ev, i) => (
                    <p key={i} className="text-xs font-mono bg-carbon-100 text-green-300 px-3 py-1.5">{ev}</p>
                  ))}
                </div>
              )}
              <div className="flex items-start gap-2 mt-2 text-xs text-green-700 bg-green-50 px-3 py-2">
                <CheckCircle size={12} className="mt-0.5 flex-shrink-0" />
                {runtimeAnalysis.root_cause_summary || 'Automation ran successfully — no errors detected.'}
              </div>
              {runtimeAnalysis.validation_steps.length > 0 && (
                <div className="mt-3">
                  <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">Post-Run Checklist</p>
                  <ol className="space-y-1">
                    {runtimeAnalysis.validation_steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-carbon-70">
                        <span className="w-5 h-5 bg-green-100 text-green-700 text-xs font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* AI detailed analysis cards */}
          {!isSuccess && (aiNarrative?.root_causes_detail?.length ?? 0) > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-carbon-90 flex items-center gap-2">
                <Bug size={14} className="text-ibm-blue60" />
                Detailed Analysis — {aiNarrative!.root_causes_detail!.length} failure{aiNarrative!.root_causes_detail!.length !== 1 ? 's' : ''} identified
              </h3>
              {aiNarrative!.root_causes_detail!.map((detail: AINarrativeCause, i: number) => (
                <div key={i} className="card border border-carbon-20 p-5 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <h4 className="text-sm font-semibold text-carbon-100">{detail.title}</h4>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {detail.failure_category && (
                        <span className={clsx('badge text-xs', FAILURE_CAT_COLOR[detail.failure_category] ?? 'bg-carbon-10 text-carbon-70')}>
                          {detail.failure_category}
                        </span>
                      )}
                      {detail.confidence_label && (
                        <span className={clsx('badge text-xs font-semibold',
                          detail.confidence_label === 'High'   ? 'bg-green-100 text-green-800' :
                          detail.confidence_label === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-carbon-10 text-carbon-60'
                        )}>
                          {detail.confidence_label} Confidence
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    {detail.affected_workflow && (
                      <div className="bg-carbon-10 p-2.5">
                        <p className="font-semibold text-carbon-60 mb-0.5 flex items-center gap-1"><GitBranch size={10} /> Workflow / Process</p>
                        <p className="font-mono text-carbon-100">{detail.affected_workflow}</p>
                      </div>
                    )}
                    {detail.affected_activity && (
                      <div className="bg-carbon-10 p-2.5">
                        <p className="font-semibold text-carbon-60 mb-0.5 flex items-center gap-1"><Code2 size={10} /> Activity / Stage</p>
                        <p className="font-mono text-carbon-100">{detail.affected_activity}</p>
                      </div>
                    )}
                  </div>
                  {detail.what_was_happening && (
                    <div>
                      <p className="text-2xs font-semibold text-carbon-50 uppercase tracking-widest mb-1">What was happening</p>
                      <p className="text-sm text-carbon-70">{detail.what_was_happening}</p>
                    </div>
                  )}
                  {detail.why_it_failed && (
                    <div>
                      <p className="text-2xs font-semibold text-carbon-50 uppercase tracking-widest mb-1">Why it failed</p>
                      <p className="text-sm text-carbon-70">{detail.why_it_failed}</p>
                    </div>
                  )}
                  {detail.confidence_reasoning && (
                    <div className="flex items-start gap-2 text-xs text-carbon-60 bg-carbon-10 px-3 py-2">
                      <Info size={11} className="flex-shrink-0 mt-0.5" />
                      <span><strong>Confidence reasoning:</strong> {detail.confidence_reasoning}</span>
                    </div>
                  )}
                  {(detail.suggested_checks?.length ?? 0) > 0 && (
                    <div>
                      <p className="text-2xs font-semibold text-carbon-50 uppercase tracking-widest mb-2">Suggested Checks</p>
                      <ol className="space-y-1">
                        {detail.suggested_checks.map((chk: string, j: number) => (
                          <li key={j} className="flex items-start gap-2 text-xs text-carbon-70">
                            <span className="w-4 h-4 bg-ibm-blue10 text-ibm-blue70 text-2xs font-bold flex items-center justify-center flex-shrink-0">{j + 1}</span>
                            {chk}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                  {detail.suggested_fix && (
                    <div className="bg-ibm-blue10 border border-ibm-blue20 p-3">
                      <p className="text-xs font-semibold text-ibm-blue70 mb-1 flex items-center gap-1">
                        <ShieldCheck size={11} /> Recommended Fix
                      </p>
                      <p className="text-sm text-ibm-blue70">{detail.suggested_fix}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Heuristic root causes */}
          {rootCauses.filter(rc => rc.category !== 'ProjectInfo').length > 0 && (
            <div className="space-y-3">
              {(aiNarrative?.root_causes_detail?.length ?? 0) === 0 && !isSuccess && (
                <h3 className="text-sm font-semibold text-carbon-90 flex items-center gap-2">
                  <Bug size={14} className="text-carbon-50" />
                  {hasLog ? 'Root Causes Identified' : 'Potential Risks (Static Analysis)'}
                </h3>
              )}
              {rootCauses.filter(rc => rc.category !== 'ProjectInfo').map((rc, i) => (
                <div key={i} className={clsx(
                  'card border-l-4 border border-carbon-20',
                  rc.severity === 'critical' ? 'border-l-red-500' :
                  rc.severity === 'high'     ? 'border-l-orange-500' :
                  rc.severity === 'medium'   ? 'border-l-yellow-500' : 'border-l-green-500'
                )}>
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`badge border ${SEVERITY_STYLES[rc.severity]}`}>{rc.severity.toUpperCase()}</span>
                          <span className="badge bg-carbon-10 text-carbon-70">{rc.category}</span>
                          {rc.affected_workflow && (
                            <span className="font-mono text-2xs bg-ibm-blue10 text-ibm-blue70 px-2 py-0.5">{rc.affected_workflow}</span>
                          )}
                        </div>
                        <h4 className="text-sm font-semibold text-carbon-100">#{i + 1} {rc.title}</h4>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-2xl font-light text-carbon-100">{Math.round(rc.confidence * 100)}%</p>
                        <p className="text-xs text-carbon-50">confidence</p>
                      </div>
                    </div>
                    <p className="text-sm text-carbon-70 leading-relaxed mb-4">{rc.description}</p>
                    {(rc.affected_workflow || rc.affected_activity) && (
                      <div className="flex items-center gap-4 text-xs text-carbon-60 mb-4 bg-carbon-10 px-3 py-2">
                        {rc.affected_workflow && (
                          <span className="flex items-center gap-1.5">
                            <GitBranch size={11} className="text-ibm-blue60" />
                            <strong>Workflow:</strong> <span className="font-mono">{rc.affected_workflow}</span>
                          </span>
                        )}
                        {rc.affected_activity && (
                          <span className="flex items-center gap-1.5">
                            <Code2 size={11} className="text-carbon-50" />
                            <strong>Activity:</strong> <span className="font-mono">{rc.affected_activity}</span>
                          </span>
                        )}
                      </div>
                    )}
                    {rc.evidence.length > 0 && (
                      <div className="mb-4">
                        <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">Evidence</p>
                        <div className="space-y-1">
                          {rc.evidence.slice(0, 5).map((ev, j) => (
                            <p key={j} className="text-xs font-mono bg-carbon-100 text-green-300 px-3 py-1.5">{ev}</p>
                          ))}
                        </div>
                      </div>
                    )}
                    {rc.suggested_fix && (
                      <div className="bg-ibm-blue10 border border-ibm-blue20 p-3 mb-3">
                        <p className="text-xs font-semibold text-ibm-blue70 mb-1">Suggested Fix</p>
                        <p className="text-sm text-ibm-blue70">{rc.suggested_fix}</p>
                      </div>
                    )}
                    {rc.preventive_recommendations.length > 0 && (
                      <div>
                        <p className="text-2xs font-semibold text-carbon-60 uppercase tracking-widest mb-2">Preventive Recommendations</p>
                        <ul className="space-y-1.5">
                          {rc.preventive_recommendations.map((r, j) => (
                            <li key={j} className="flex items-start gap-2 text-sm text-carbon-70">
                              <CheckCircle size={13} className="text-green-600 mt-0.5 flex-shrink-0" /> {r}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!isSuccess && rcaCount === 0 && (
            <div className="card p-8 text-center text-carbon-50 text-sm">
              No root causes identified — upload an execution log or paste an error for runtime diagnosis.
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-carbon-90 mb-4">Action Items &amp; Recommendations</h3>
              <ol className="space-y-2">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-carbon-70">
                    <span className="w-5 h-5 bg-ibm-blue10 text-ibm-blue70 text-xs font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
                    {rec}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      {/* ══════════ CODING STANDARDS TAB ══════════════════════════════════════ */}
      {activeTab === 'standards' && (
        <div className="space-y-4">
          {violations.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={36} className="mx-auto text-green-600 mb-3" />
              <p className="text-base font-semibold text-carbon-100">All standards passed!</p>
              <p className="text-sm text-carbon-60 mt-1">No coding standard violations were found in this project.</p>
            </div>
          ) : (
            <>
              {(['critical', 'high', 'medium', 'low'] as const).map(sev => {
                const sevViolations = violations.filter((v: StandardsViolation) => v.severity === sev)
                if (sevViolations.length === 0) return null
                return (
                  <div key={sev}>
                    <h3 className="flex items-center gap-2 text-xs font-bold text-carbon-70 mb-2 uppercase tracking-widest">
                      <span className={clsx('w-2.5 h-2.5', SEVERITY_DOT[sev])} />
                      {sev} ({sevViolations.length})
                    </h3>
                    <div className="space-y-2">
                      {sevViolations.map((v: StandardsViolation, i: number) => (
                        <div key={i} className={clsx('card border-l-4 border border-carbon-20',
                          sev === 'critical' ? 'border-l-red-500' : sev === 'high' ? 'border-l-orange-500' :
                          sev === 'medium'   ? 'border-l-yellow-500' : 'border-l-green-500'
                        )}>
                          <div className="p-4">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-mono text-xs font-bold text-carbon-60">{v.rule_id}</span>
                                  <span className={`badge border text-xs ${SEVERITY_STYLES[sev]}`}>{sev.toUpperCase()}</span>
                                </div>
                                <p className="text-sm font-semibold text-carbon-100">{v.rule_name}</p>
                                <p className="text-xs text-carbon-60 mt-1">{v.description}</p>
                              </div>
                              <ChevronRight size={16} className="text-carbon-40 flex-shrink-0 mt-1" />
                            </div>
                            <div className="flex items-center gap-1.5 mt-3 text-xs text-carbon-60">
                              <Code2 size={11} />
                              <span className="font-medium">Location:</span>
                              <span className="font-mono bg-carbon-10 px-1.5 py-0.5">{v.location}</span>
                              <span className="text-carbon-40">({v.location_type})</span>
                            </div>
                            <div className="mt-3 bg-ibm-blue10 p-3">
                              <p className="text-xs font-semibold text-ibm-blue70 mb-1 flex items-center gap-1">
                                <Info size={11} /> Recommendation
                              </p>
                              <p className="text-xs text-ibm-blue70">{v.recommendation}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
              {(report.standards_violations?.passed_rules?.length ?? 0) > 0 && (
                <div className="card p-4">
                  <p className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1.5">
                    <CheckCircle size={13} /> Passed Rules ({report.standards_violations!.passed_rules.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {report.standards_violations!.passed_rules.map((r, i) => (
                      <span key={i} className="font-mono text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5">{r}</span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ══════════ CODE ERRORS TAB ═══════════════════════════════════════════ */}
      {activeTab === 'code-errors' && (
        <div className="space-y-4">
          {codeErrors.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={36} className="mx-auto text-green-600 mb-3" />
              <p className="text-base font-semibold text-carbon-100">No code errors detected</p>
              <p className="text-sm text-carbon-60 mt-1">Static analysis found no errors in the parsed project structure.</p>
            </div>
          ) : (
            codeErrors.map((ce: CodeError, i: number) => (
              <div key={i} className={clsx('card border-l-4 border border-carbon-20',
                ce.severity === 'critical' ? 'border-l-red-500' : ce.severity === 'high' ? 'border-l-orange-500' :
                ce.severity === 'medium'   ? 'border-l-yellow-500' : 'border-l-green-500'
              )}>
                <div className="p-5">
                  <div className="flex items-start gap-3 mb-3">
                    <div className={clsx('w-8 h-8 flex items-center justify-center flex-shrink-0', SEVERITY_STYLES[ce.severity])}>
                      <Bug size={15} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`badge border ${SEVERITY_STYLES[ce.severity]}`}>{ce.severity.toUpperCase()}</span>
                        <span className="font-mono text-xs text-carbon-60 bg-carbon-10 px-2 py-0.5">{ce.error_type}</span>
                      </div>
                      <h4 className="text-sm font-semibold text-carbon-100">{ce.title}</h4>
                    </div>
                  </div>
                  <p className="text-sm text-carbon-70 leading-relaxed mb-3">{ce.description}</p>
                  <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
                    <div className="bg-carbon-10 p-2.5">
                      <p className="font-semibold text-carbon-60 mb-0.5">Location</p>
                      <p className="font-mono text-carbon-100">{ce.location}</p>
                    </div>
                    <div className="bg-carbon-10 p-2.5">
                      <p className="font-semibold text-carbon-60 mb-0.5">Activity / Stage</p>
                      <p className="font-mono text-carbon-100">{ce.line_hint || '—'}</p>
                    </div>
                  </div>
                  <div className="bg-ibm-blue10 border border-ibm-blue20 p-3">
                    <p className="text-xs font-semibold text-ibm-blue70 mb-1">How to Fix</p>
                    <p className="text-sm text-ibm-blue70">{ce.fix}</p>
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
