import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { adminMetrics, type Metric } from '@/lib/data'
import { cn } from '@/lib/utils'

const toneRing: Record<NonNullable<Metric['tone']>, string> = {
  default: 'ring-foreground/10',
  high: 'ring-high/30',
  resolved: 'ring-resolved/30',
}

const toneValue: Record<NonNullable<Metric['tone']>, string> = {
  default: 'text-foreground',
  high: 'text-high',
  resolved: 'text-resolved',
}

export function MetricCards() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {adminMetrics.map((m) => {
        const tone = m.tone ?? 'default'
        const TrendIcon =
          m.trend === 'up'
            ? ArrowUpRight
            : m.trend === 'down'
              ? ArrowDownRight
              : Minus
        return (
          <div
            key={m.label}
            className={cn(
              'relative flex flex-col gap-2 rounded-2xl bg-card/60 p-4 ring-1',
              toneRing[tone],
            )}
          >
            {tone === 'high' && (
              <span className="absolute top-4 right-4 size-2 rounded-full bg-high animate-ai-blink" />
            )}
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {m.label}
            </span>
            <span
              className={cn(
                'text-3xl font-semibold tabular-nums tracking-tight',
                toneValue[tone],
              )}
            >
              {m.value}
            </span>
            {m.delta && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendIcon className="size-3.5" />
                {m.delta}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
