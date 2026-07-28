import clsx from 'clsx'

// IBM Carbon tag colours — light background, matching text
const PLATFORM_CONFIG: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  uipath:              { label: 'UiPath',             bg: 'bg-orange-100',       text: 'text-orange-800',  dot: 'bg-orange-500' },
  power_automate:      { label: 'Power Automate',     bg: 'bg-blue-100',         text: 'text-blue-800',    dot: 'bg-ibm-blue60' },
  blue_prism:          { label: 'Blue Prism',         bg: 'bg-purple-100',       text: 'text-purple-800',  dot: 'bg-purple-600' },
  automation_anywhere: { label: 'Automation Anywhere',bg: 'bg-pink-100',         text: 'text-pink-800',    dot: 'bg-pink-500'   },
  unknown:             { label: 'Unknown',            bg: 'bg-carbon-20',        text: 'text-carbon-70',   dot: 'bg-carbon-40'  },
}

interface Props {
  platform: string
  size?: 'sm' | 'md' | 'lg'
}

export default function PlatformBadge({ platform, size = 'md' }: Props) {
  const cfg = PLATFORM_CONFIG[platform] ?? PLATFORM_CONFIG['unknown']
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 font-medium',
      cfg.bg, cfg.text,
      size === 'sm' ? 'px-2 py-0.5 text-2xs' : size === 'lg' ? 'px-3 py-1 text-xs' : 'px-2.5 py-0.5 text-2xs'
    )}>
      <span className={clsx('flex-shrink-0', cfg.dot, size === 'lg' ? 'w-2.5 h-2.5' : 'w-2 h-2')} />
      {cfg.label}
    </span>
  )
}
