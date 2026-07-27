import clsx from 'clsx'

interface Event {
  level: 'info' | 'warning' | 'error' | 'debug'
  message: string
  timestamp?: string
}

interface Props {
  events: Event[]
}

const LEVEL_STYLES = {
  info:    { dot: 'bg-blue-500',   label: 'INFO',  text: 'text-blue-700',  bg: 'bg-blue-50'  },
  warning: { dot: 'bg-yellow-500', label: 'WARN',  text: 'text-yellow-700', bg: 'bg-yellow-50' },
  error:   { dot: 'bg-red-500',    label: 'ERROR', text: 'text-red-700',   bg: 'bg-red-50'   },
  debug:   { dot: 'bg-gray-400',   label: 'DEBUG', text: 'text-gray-600',  bg: 'bg-gray-50'  },
}

export default function ExceptionTimeline({ events }: Props) {
  if (events.length === 0) {
    return <p className="text-sm text-gray-400">No timeline events available</p>
  }

  return (
    <div className="space-y-0">
      {events.map((ev, i) => {
        const style = LEVEL_STYLES[ev.level] || LEVEL_STYLES.info
        const isLast = i === events.length - 1
        const isError = ev.level === 'error'
        return (
          <div key={i} className="flex gap-3">
            {/* Line + dot */}
            <div className="flex flex-col items-center">
              <div className={clsx('w-3 h-3 rounded-full flex-shrink-0 mt-1', style.dot, isError && 'ring-2 ring-red-200')} />
              {!isLast && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
            </div>
            {/* Content */}
            <div className={clsx('flex-1 px-3 py-2 rounded-lg mb-2 text-sm', style.bg, isError && 'border border-red-200')}>
              <div className="flex items-center gap-2 mb-0.5">
                <span className={clsx('text-xs font-semibold', style.text)}>{style.label}</span>
                {ev.timestamp && <span className="text-xs text-gray-400">{ev.timestamp}</span>}
              </div>
              <p className={clsx('text-xs', isError ? 'text-red-800 font-medium' : 'text-gray-700')}>{ev.message}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
