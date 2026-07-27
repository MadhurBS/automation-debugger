import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useQuery } from '@tanstack/react-query'
import { FileText, ClipboardPaste, CheckCircle, Loader2, X, Upload, AlertTriangle } from 'lucide-react'
import { listProjects, uploadLogs, pasteErrorText } from '../api/projects'
import { triggerAnalysis } from '../api/analysis'
import toast from 'react-hot-toast'
import PlatformBadge from '../components/PlatformBadge'
import clsx from 'clsx'

const LOG_FORMATS: Record<string, string[]> = {
  uipath: ['UiPath JSON Array', 'UiPath NLog', 'Plain Text'],
  power_automate: ['JSON Lines', 'Plain Text'],
  blue_prism: ['Plain Text', 'Event Log'],
  automation_anywhere: ['JSON', 'Plain Text'],
}

const PASTE_PLACEHOLDERS: Record<string, string> = {
  uipath: `Paste your UiPath error here, e.g.:

System.NullReferenceException: Object reference not set to an instance of an object.
   at UiPath.Activities.Core.InvokeWorkflowFile.Execute(CodeActivityContext context)
   at System.Activities.CodeActivity.InternalExecute(ActivityInstance instance, ActivityExecutor executor, BookmarkManager bookmarkManager)
Message: Invoke Main workflow: Object reference not set to an instance of an object.`,
  power_automate: `Paste your Power Automate error here, e.g.:

ActionFailed. The HTTP request failed with status '400 Bad Request'.
Error: {"error":{"code":"InvalidTemplate","message":"..."}}`,
  blue_prism: `Paste your Blue Prism error here, e.g.:

Internal : Object Reference
The object reference was not set.
Stage: Get Customer Data (Action)`,
  automation_anywhere: `Paste your Automation Anywhere error here, e.g.:

Error Code: ERR_OPR_FAIL
Message: Operation failed at line 42.
Command: Get Text - Element not found`,
}

type InputMode = 'file' | 'paste'

export default function UploadLog() {
  const navigate = useNavigate()
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [inputMode, setInputMode] = useState<InputMode>('file')
  const [logFiles, setLogFiles] = useState<File[]>([])
  const [pastedText, setPastedText] = useState('')
  const [loading, setLoading] = useState(false)

  const { data: projectsData } = useQuery({
    queryKey: ['projects', 'upload-log'],
    queryFn: () => listProjects(1, 100),
  })

  const projects = projectsData?.items ?? []
  const selectedProject = projects.find(p => p.id === selectedProjectId)

  const onDrop = useCallback((files: File[]) => {
    setLogFiles(prev => [...prev, ...files].slice(0, 5))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: { 'text/plain': ['.log', '.txt'], 'application/json': ['.json'] },
  })

  const removeFile = (idx: number) => {
    setLogFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const isReady = selectedProjectId && (
    (inputMode === 'file' && logFiles.length > 0) ||
    (inputMode === 'paste' && pastedText.trim().length >= 5)
  )

  const handleAnalyze = async () => {
    if (!selectedProjectId) { toast.error('Please select a project'); return }

    setLoading(true)
    try {
      if (inputMode === 'file') {
        if (logFiles.length === 0) { toast.error('Please add at least one log file'); return }
        await uploadLogs(selectedProjectId, logFiles)
      } else {
        if (pastedText.trim().length < 5) { toast.error('Please enter an error message'); return }
        await pasteErrorText(selectedProjectId, pastedText.trim())
      }

      const analysis = await triggerAnalysis(selectedProjectId)
      toast.success('Analysis started!')
      navigate(`/analysis/${analysis.id}/progress`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to start analysis'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Debug with Logs or Error Message</h2>
        <p className="text-sm text-gray-500 mt-0.5">Upload an execution log file <em>or</em> paste an error message to start root cause analysis</p>
      </div>

      {/* Project selector */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Select Project <span className="text-red-500">*</span></h3>
        {projects.length === 0 ? (
          <p className="text-sm text-gray-500">
            No projects found.{' '}
            <button onClick={() => navigate('/upload/project')} className="text-primary-600 hover:underline">
              Upload a project first.
            </button>
          </p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {projects.map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedProjectId(p.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-all ${
                  selectedProjectId === p.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <PlatformBadge platform={p.platform} size="sm" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{p.name}</p>
                  <p className="text-xs text-gray-500 truncate">{p.original_filename}</p>
                </div>
                {selectedProjectId === p.id && <CheckCircle size={16} className="text-primary-600 flex-shrink-0" />}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Format hint */}
      {selectedProject && (
        <div className="flex items-start gap-2 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-700">
          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5 text-blue-500" />
          <span>
            <strong>Supported log formats for {selectedProject.platform}:</strong>{' '}
            {(LOG_FORMATS[selectedProject.platform] || ['JSON', 'Plain Text']).join(' · ')}
          </span>
        </div>
      )}

      {/* Input mode toggle */}
      <div className="card p-5">
        <div className="flex bg-gray-100 rounded-lg p-1 mb-5">
          {(['file', 'paste'] as InputMode[]).map(mode => (
            <button
              key={mode}
              onClick={() => setInputMode(mode)}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-md transition-all',
                inputMode === mode
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              {mode === 'file' ? <Upload size={14} /> : <ClipboardPaste size={14} />}
              {mode === 'file' ? 'Upload Log File' : 'Paste Error Message'}
            </button>
          ))}
        </div>

        {/* ── File upload tab ── */}
        {inputMode === 'file' && (
          <div className="space-y-3">
            {logFiles.length > 0 && (
              <div className="space-y-2">
                {logFiles.map((f, i) => (
                  <div key={i} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded-lg border border-gray-200">
                    <FileText size={16} className="text-gray-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-800 truncate">{f.name}</p>
                      <p className="text-xs text-gray-500">{(f.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-red-500">
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
              }`}
            >
              <input {...getInputProps()} />
              <FileText size={28} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm font-medium text-gray-700">Drop log files here</p>
              <p className="text-xs text-gray-500 mt-1">or click to browse · .log, .txt, .json · up to 5 files</p>
            </div>
          </div>
        )}

        {/* ── Paste error tab ── */}
        {inputMode === 'paste' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-500">Paste the full error message, stack trace, or exception details below</p>
              {pastedText.trim().length > 0 && (
                <button
                  onClick={() => setPastedText('')}
                  className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1"
                >
                  <X size={12} /> Clear
                </button>
              )}
            </div>
            <textarea
              value={pastedText}
              onChange={e => setPastedText(e.target.value)}
              rows={12}
              placeholder={PASTE_PLACEHOLDERS[selectedProject?.platform || 'uipath'] || PASTE_PLACEHOLDERS.uipath}
              className="w-full px-3 py-2.5 text-xs font-mono border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y bg-gray-950 text-green-300 placeholder-gray-600 leading-relaxed"
            />
            {pastedText.trim().length > 0 && (
              <div className="flex items-center gap-2 text-xs">
                <CheckCircle size={13} className="text-green-500" />
                <span className="text-gray-600">
                  {pastedText.trim().length} characters · ready to analyze
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <button
        onClick={handleAnalyze}
        disabled={loading || !isReady}
        className="btn-primary w-full justify-center py-2.5"
      >
        {loading
          ? <Loader2 size={16} className="animate-spin" />
          : inputMode === 'file' ? <FileText size={16} /> : <ClipboardPaste size={16} />
        }
        {loading
          ? 'Analyzing...'
          : inputMode === 'file' ? 'Upload Logs & Analyze' : 'Analyze Pasted Error'
        }
      </button>
    </div>
  )
}
