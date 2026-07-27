import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileArchive, CheckCircle, Loader2, X, ClipboardPaste,
  Cpu, ChevronDown, ChevronUp, AlertCircle,
} from 'lucide-react'
import { uploadProject, uploadLogs, pasteErrorText, detectPlatform } from '../api/projects'
import { triggerAnalysis } from '../api/analysis'
import toast from 'react-hot-toast'
import PlatformBadge from '../components/PlatformBadge'
import clsx from 'clsx'

const PLATFORMS = [
  { id: 'uipath',              label: 'UiPath' },
  { id: 'power_automate',      label: 'Power Automate' },
  { id: 'blue_prism',          label: 'Blue Prism' },
  { id: 'automation_anywhere', label: 'Automation Anywhere' },
]

type LogMode = 'file' | 'paste'
type DetectionState = 'idle' | 'detecting' | 'done' | 'error'

export default function UploadProject() {
  const navigate = useNavigate()

  // Project file
  const [projectFile, setProjectFile]           = useState<File | null>(null)

  // Auto-detection state
  const [detectionState, setDetectionState]     = useState<DetectionState>('idle')
  const [detectedPlatform, setDetectedPlatform] = useState<string>('unknown')
  const [detectedConfidence, setDetectedConfidence] = useState<number>(0)
  const [overridePlatform, setOverridePlatform] = useState<string>('')
  const [showOverride, setShowOverride]         = useState(false)

  // Effective platform — override wins if set, otherwise auto-detected
  const effectivePlatform = overridePlatform || detectedPlatform

  // Log / paste
  const [logFile, setLogFile]     = useState<File | null>(null)
  const [logMode, setLogMode]     = useState<LogMode>('file')
  const [pastedError, setPastedError] = useState('')

  // Metadata
  const [name, setName]               = useState('')
  const [description, setDescription] = useState('')

  // Upload state
  const [loading, setLoading]               = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)

  // ── Drop handlers ─────────────────────────────────────────────────────────

  const onDropProject = useCallback(async (files: File[]) => {
    const file = files[0]
    if (!file) return
    setProjectFile(file)
    // Use functional updater so we don't need `name` in the dep array
    setName(prev => prev || file.name.replace(/\.[^.]+$/, ''))

    // Kick off auto-detection immediately
    setDetectionState('detecting')
    setDetectedPlatform('unknown')
    setDetectedConfidence(0)
    setOverridePlatform('')
    setShowOverride(false)

    try {
      const result = await detectPlatform(file)
      setDetectedPlatform(result.platform)
      setDetectedConfidence(result.confidence)
      setDetectionState('done')
    } catch (err: unknown) {
      console.error('Platform detection failed:', err)
      setDetectionState('error')
    }
  }, [])

  const onDropLog = useCallback((files: File[]) => {
    if (files[0]) setLogFile(files[0])
  }, [])

  const { getRootProps: getProjProps, getInputProps: getProjInput, isDragActive: isProjDrag } =
    useDropzone({
      onDrop: onDropProject,
      multiple: false,
      accept: {
        'application/zip':  ['.zip'],
        'application/xml':  ['.xml', '.xaml', '.bprelease'],
        'application/json': ['.json'],
        'application/octet-stream': ['.nupkg', '.atmx', '.mbot'],
      },
    })

  const { getRootProps: getLogProps, getInputProps: getLogInput, isDragActive: isLogDrag } =
    useDropzone({ onDrop: onDropLog, multiple: false, accept: { 'text/plain': ['.txt', '.log'], 'application/json': ['.json'] } })

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!projectFile) { toast.error('Please select a project file'); return }
    if (!name.trim())  { toast.error('Please enter a project name'); return }

    setLoading(true)
    setUploadProgress(10)
    try {
      const fd = new FormData()
      fd.append('file', projectFile)
      fd.append('name', name)
      fd.append('description', description)
      // Send override if set, otherwise send 'unknown' so backend auto-detects
      fd.append('platform', overridePlatform || 'unknown')

      setUploadProgress(30)
      const project = await uploadProject(fd)
      setUploadProgress(60)

      if (logMode === 'file' && logFile) {
        await uploadLogs(project.id, [logFile])
        setUploadProgress(80)
      } else if (logMode === 'paste' && pastedError.trim().length >= 5) {
        await pasteErrorText(project.id, pastedError.trim())
        setUploadProgress(80)
      }

      const analysis = await triggerAnalysis(project.id)
      setUploadProgress(100)
      toast.success('Project uploaded — analysis started!')
      navigate(`/analysis/${analysis.id}/progress`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed'
      toast.error(msg)
      setUploadProgress(0)
    } finally {
      setLoading(false)
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  const confidencePct = Math.round(detectedConfidence * 100)
  const confidenceColor =
    detectedConfidence >= 0.7 ? 'text-green-700 bg-green-50 border-green-200' :
    detectedConfidence >= 0.4 ? 'text-yellow-700 bg-yellow-50 border-yellow-200' :
                                 'text-red-700 bg-red-50 border-red-200'

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Upload Project</h2>
        <p className="text-sm text-gray-500 mt-0.5">Upload an RPA project for AI-powered root cause analysis</p>
      </div>

      {/* ── Project file dropzone ─────────────────────────────────────── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Project File <span className="text-red-500">*</span>
        </h3>

        {projectFile ? (
          <div className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle size={18} className="text-green-600 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{projectFile.name}</p>
              <p className="text-xs text-gray-500">{(projectFile.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button
              onClick={() => {
                setProjectFile(null)
                setDetectionState('idle')
                setDetectedPlatform('unknown')
                setDetectedConfidence(0)
                setOverridePlatform('')
                setShowOverride(false)
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          </div>
        ) : (
          <div
            {...getProjProps()}
            className={clsx(
              'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors',
              isProjDrag
                ? 'border-primary-400 bg-primary-50'
                : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
            )}
          >
            <input {...getProjInput()} />
            <FileArchive size={32} className="mx-auto text-gray-400 mb-3" />
            <p className="text-sm font-medium text-gray-700">Drop your project ZIP here</p>
            <p className="text-xs text-gray-500 mt-1">or click to browse — ZIP, XAML, JSON, XML, BPRELEASE, NUPKG</p>
          </div>
        )}
      </div>

      {/* ── Platform detection panel (shown after file dropped) ────────── */}
      {detectionState !== 'idle' && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Cpu size={15} className="text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-900">Platform Detection</h3>
          </div>

          {detectionState === 'detecting' && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 size={15} className="animate-spin text-primary-500" />
              Analysing file structure…
            </div>
          )}

          {detectionState === 'error' && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle size={15} />
              Detection failed — please select a platform manually below.
            </div>
          )}

          {detectionState === 'done' && (
            <div className="space-y-3">
              {/* Detected result */}
              <div className={clsx('flex items-center gap-3 px-3 py-2.5 rounded-lg border text-sm', confidenceColor)}>
                {overridePlatform ? (
                  <>
                    <PlatformBadge platform={overridePlatform} size="sm" />
                    <span className="font-medium flex-1">
                      {PLATFORMS.find(p => p.id === overridePlatform)?.label ?? overridePlatform}
                    </span>
                    <span className="text-xs font-medium uppercase tracking-wide opacity-70">Override</span>
                  </>
                ) : detectedPlatform === 'unknown' ? (
                  <>
                    <AlertCircle size={16} className="text-yellow-500" />
                    <span className="flex-1 text-yellow-700">Could not detect platform — please select manually</span>
                  </>
                ) : (
                  <>
                    <PlatformBadge platform={detectedPlatform} size="sm" />
                    <span className="font-medium flex-1">
                      {PLATFORMS.find(p => p.id === detectedPlatform)?.label ?? detectedPlatform}
                    </span>
                    <span className="text-xs font-medium">{confidencePct}% confidence</span>
                  </>
                )}
              </div>

              {/* Confidence bar (only for auto-detect, not override) */}
              {!overridePlatform && detectedPlatform !== 'unknown' && (
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      'h-full rounded-full transition-all duration-500',
                      detectedConfidence >= 0.7 ? 'bg-green-500' :
                      detectedConfidence >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'
                    )}
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
              )}

              {/* Override toggle */}
              <button
                onClick={() => setShowOverride(v => !v)}
                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mt-1"
              >
                {showOverride ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                {overridePlatform ? 'Change override' : 'Override detected platform'}
              </button>

              {showOverride && (
                <div className="grid grid-cols-2 gap-2 pt-1">
                  {/* "Use auto" option */}
                  <button
                    onClick={() => { setOverridePlatform(''); setShowOverride(false) }}
                    className={clsx(
                      'flex items-center gap-2 p-2.5 rounded-lg border text-left transition-all text-xs',
                      !overridePlatform
                        ? 'border-primary-500 bg-primary-50 text-primary-700 font-medium'
                        : 'border-gray-200 hover:border-gray-300 text-gray-600'
                    )}
                  >
                    <Cpu size={14} className="flex-shrink-0" />
                    Auto-detected
                  </button>
                  {PLATFORMS.map(p => (
                    <button
                      key={p.id}
                      onClick={() => { setOverridePlatform(p.id); setShowOverride(false) }}
                      className={clsx(
                        'flex items-center gap-2 p-2.5 rounded-lg border text-left transition-all',
                        overridePlatform === p.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      )}
                    >
                      <PlatformBadge platform={p.id} size="sm" />
                      <span className={clsx(
                        'text-xs font-medium',
                        overridePlatform === p.id ? 'text-primary-700' : 'text-gray-700'
                      )}>{p.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Execution log / paste error ───────────────────────────────── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-gray-900">
            Execution Log <span className="text-gray-400 font-normal">(optional)</span>
          </h3>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          Attach a log file <em>or</em> paste an error message — improves root cause accuracy
        </p>

        {/* Mode toggle */}
        <div className="flex bg-gray-100 rounded-lg p-1 mb-4">
          {(['file', 'paste'] as LogMode[]).map(m => (
            <button
              key={m}
              onClick={() => setLogMode(m)}
              className={clsx(
                'flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-all',
                logMode === m ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              )}
            >
              {m === 'file' ? <Upload size={12} /> : <ClipboardPaste size={12} />}
              {m === 'file' ? 'Upload File' : 'Paste Error'}
            </button>
          ))}
        </div>

        {logMode === 'file' && (
          logFile ? (
            <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <CheckCircle size={18} className="text-blue-600 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{logFile.name}</p>
                <p className="text-xs text-gray-500">{(logFile.size / 1024).toFixed(1)} KB</p>
              </div>
              <button onClick={() => setLogFile(null)} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
            </div>
          ) : (
            <div
              {...getLogProps()}
              className={clsx(
                'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors',
                isLogDrag
                  ? 'border-primary-400 bg-primary-50'
                  : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
              )}
            >
              <input {...getLogInput()} />
              <Upload size={24} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-600">Drop log file here (.log, .txt, .json)</p>
            </div>
          )
        )}

        {logMode === 'paste' && (
          <div className="space-y-2">
            <textarea
              value={pastedError}
              onChange={e => setPastedError(e.target.value)}
              rows={7}
              placeholder={`Paste error message or stack trace here...\n\ne.g. System.NullReferenceException: Object reference not set...\n   at UiPath.Core.Activities...`}
              className="w-full px-3 py-2.5 text-xs font-mono border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y bg-gray-950 text-green-300 placeholder-gray-600 leading-relaxed"
            />
            {pastedError.trim().length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-green-700">
                <CheckCircle size={12} /> {pastedError.trim().length} chars ready
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Project metadata ─────────────────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-gray-900">Project Details</h3>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project Name <span className="text-red-500">*</span>
          </label>
          <input
            className="input"
            placeholder="e.g. Invoice Processing Bot"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            className="input resize-none"
            rows={2}
            placeholder="Brief description of what the automation does..."
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
        </div>
      </div>

      {/* ── Upload progress ───────────────────────────────────────────────── */}
      {loading && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-700">Uploading &amp; starting analysis…</span>
            <span className="text-sm font-medium text-primary-600">{uploadProgress}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading || !projectFile || detectionState === 'detecting'}
        className="btn-primary w-full justify-center py-2.5"
      >
        {loading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
        {loading ? 'Uploading…' : detectionState === 'detecting' ? 'Detecting platform…' : 'Upload & Analyze'}
      </button>
    </div>
  )
}
