import clsx from 'clsx'

const PLATFORM_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  uipath:              { label: 'UiPath',             color: 'bg-orange-100 text-orange-800', dot: 'bg-orange-500' },
  power_automate:      { label: 'Power Automate',     color: 'bg-blue-100 text-blue-800',    dot: 'bg-blue-500'   },
  blue_prism:          { label: 'Blue Prism',         color: 'bg-purple-100 text-purple-800', dot: 'bg-purple-600' },
  automation_anywhere: { label: 'Automation Anywhere', color: 'bg-pink-100 text-pink-800',   dot: 'bg-pink-500'   },
  unknown:             { label: 'Unknown',            color: 'bg-gray-100 text-gray-600',    dot: 'bg-gray-400'   },
}

interface Props {
  platform: string
  size?: 'sm' | 'md' | 'lg'
}

export default function PlatformBadge({ platform, size = 'md' }: Props) {
  const config = PLATFORM_CONFIG[platform] || PLATFORM_CONFIG['unknown']
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full font-medium',
      config.color,
      size === 'sm' ? 'px-2 py-0.5 text-xs' : size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2.5 py-0.5 text-xs'
    )}>
      <span className={clsx('rounded-full flex-shrink-0', config.dot, size === 'lg' ? 'w-2.5 h-2.5' : 'w-2 h-2')} />
      {config.label}
    </span>
  )
}
