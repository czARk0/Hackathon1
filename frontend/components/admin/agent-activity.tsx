import { Check, LoaderCircle, TriangleAlert } from 'lucide-react'
import { agentActivity, type ActivityItem } from '@/lib/data'
import { cn } from '@/lib/utils'

const kindStyles: Record<
  ActivityItem['kind'],
  { ring: string; text: string; Icon: typeof Check }
> = {
  done: { ring: 'bg-resolved/15 text-resolved ring-resolved/25', text: 'text-foreground', Icon: Check },
  active: { ring: 'bg-primary/15 text-primary ring-primary/25', text: 'text-foreground', Icon: LoaderCircle },
  warn: { ring: 'bg-high/15 text-high ring-high/25', text: 'text-high', Icon: TriangleAlert },
}

export function AgentActivity() {
  return (
    <div className="flex h-full flex-col rounded-2xl bg-card/60 ring-1 ring-foreground/10">
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ai-pulse-ring rounded-full bg-primary" />
            <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
          </span>
          <h2 className="text-sm font-semibold">Agent activity</h2>
        </div>
        <span className="font-mono text-xs text-muted-foreground">live</span>
      </div>

      <ol className="relative flex-1 px-4 py-3">
        {agentActivity.map((item, i) => {
          const s = kindStyles[item.kind]
          const last = i === agentActivity.length - 1
          return (
            <li key={item.id} className="relative flex gap-3 pb-4 last:pb-0">
              {!last && (
                <span className="absolute top-7 left-[13px] h-[calc(100%-1rem)] w-px bg-border" />
              )}
              <span
                className={cn(
                  'relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full ring-1',
                  s.ring,
                )}
              >
                <s.Icon
                  className={cn('size-3.5', item.kind === 'active' && 'animate-spin')}
                />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className={cn('truncate text-sm font-medium', s.text)}>
                    {item.text}
                  </span>
                  <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                    {item.time}
                  </span>
                </div>
                <p className="truncate text-xs text-muted-foreground">
                  {item.meta}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
