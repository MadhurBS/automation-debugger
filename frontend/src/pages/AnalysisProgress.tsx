import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, Loader2, XCircle, Clock } from 'lucide-react'
import { getAnalysisStatus } from '../api/analysis'
import clsx from 'clsx'

const STEPS = [
  { key: 'pending', label: 'Queued', desc: 'Analysis request received' },
  { key: 'parsing', label: 'Parsing Project', desc: 'Reading project structure & workflows' },
  { key: 'analyzing', label: 'Analyzing Logs', desc: 'Extracting exceptions & execution trace' },
  { key: 'completed', label: 'AI Analysis Complete', desc: 'Root cause identified' },
]

const STATUS_ORDER = ['pending', 'parsing', 'analyzing', 'completed']

export default function AnalysisProgress() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, error } = useQuery({
    queryKey: ['analysis-status', id],
    queryFn: () => getAnalysisStatus(id!),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') return false
      return 2500
    },
    enabled: !!id,
  })

  useEffect(() => {
    if (data?.status === 'completed') {
      setTimeout(() => navigate(`/analysis/${id}/results`), 1000)
    }
  }, [data?.status, id, navigate])

  const currentStep = data?.status || 'pending'
  const isFailed = currentStep === 'failed'
  const currentIdx = STATUS_ORDER.indexOf(currentStep)

  return (
    <div className="max-w-xl mx-auto">
      <div className="card p-8">
        <div className="text-center mb-8">
          {isFailed ? (
            <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <XCircle size={28} className="text-red-600" />
            </div>
          ) : currentStep === 'completed' ? (
            <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle size={28} className="text-green-600" />
            </div>
          ) : (
            <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center mx-auto mb-4">
              <Loader2 size={28} className="text-primary-600 animate-spin" />
            </div>
          )}
          <h2 className="text-xl font-bold text-gray-900">
            {isFailed ? 'Analysis Failed' : currentStep === 'completed' ? 'Analysis Complete!' : 'Analyzing...'}
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {isFailed ? data?.error_message || 'An error occurred during analysis' : 'This usually takes 10–30 seconds'}
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-1">
          {STEPS.map((step, idx) => {
            const stepIdx = STATUS_ORDER.indexOf(step.key)
            const isCompleted = currentIdx > stepIdx || currentStep === 'completed'
            const isCurrent = step.key === currentStep && !isFailed
            const isPending = stepIdx > currentIdx && !isFailed

            return (
              <div key={step.key} className="flex items-start gap-3 py-3 relative">
                {idx < STEPS.length - 1 && (
                  <div className={clsx(
                    'absolute left-[18px] top-9 w-0.5 h-6',
                    isCompleted ? 'bg-green-300' : 'bg-gray-200'
                  )} />
                )}
                <div className={clsx(
                  'w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold',
                  isFailed && isCurrent ? 'bg-red-100 text-red-600' :
                  isCompleted ? 'bg-green-500 text-white' :
                  isCurrent ? 'bg-primary-500 text-white' :
                  'bg-gray-100 text-gray-400'
                )}>
                  {isCompleted ? <CheckCircle size={16} /> :
                   isCurrent && !isFailed ? <Loader2 size={16} className="animate-spin" /> :
                   isFailed && isCurrent ? <XCircle size={16} /> :
                   <Clock size={16} />}
                </div>
                <div className="flex-1 pt-1.5">
                  <p className={clsx(
                    'text-sm font-medium',
                    isCompleted ? 'text-green-700' :
                    isCurrent && !isFailed ? 'text-primary-700' :
                    isPending ? 'text-gray-400' : 'text-gray-700'
                  )}>{step.label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{step.desc}</p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Actions */}
        <div className="mt-6 pt-5 border-t border-gray-100 flex gap-3">
          {isFailed ? (
            <>
              <button onClick={() => navigate('/upload/project')} className="btn-primary flex-1 justify-center">
                Try Again
              </button>
              <button onClick={() => navigate('/history')} className="btn-secondary flex-1 justify-center">
                View History
              </button>
            </>
          ) : currentStep === 'completed' ? (
            <button onClick={() => navigate(`/analysis/${id}/results`)} className="btn-primary flex-1 justify-center">
              View Results
            </button>
          ) : (
            <button onClick={() => navigate('/history')} className="btn-secondary flex-1 justify-center">
              Continue in background
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
