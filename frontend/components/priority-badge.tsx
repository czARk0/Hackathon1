import { cn } from '@/lib/utils'
import type { Priority } from '@/lib/data'

const styles: Record<Priority, string> = {
  high: 'bg-high/15 text-high ring-high/30',
  medium: 'bg-medium/15 text-medium ring-medium/30',
  low: 'bg-low/15 text-low ring-low/30',
  resolved: 'bg-resolved/15 text-resolved ring-resolved/30',
}

const labels: Record<Priority, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  resolved: 'Resolved',
}

export function PriorityDot({
  priority,
  className,
}: {
  priority: Priority
  className?: string
}) {
  const color: Record<Priority, string> = {
    high: 'bg-high',
    medium: 'bg-medium',
    low: 'bg-low',
    resolved: 'bg-resolved',
  }
  return (
    <span
      className={cn('size-2 shrink-0 rounded-full', color[priority], className)}
      aria-hidden="true"
    />
  )
}

export function PriorityBadge({
  priority,
  className,
}: {
  priority: Priority
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        styles[priority],
        className,
      )}
    >
      <PriorityDot priority={priority} />
      {labels[priority]}
    </span>
  )
}
