'use client'

import {
  Brain,
  Check,
  Database,
  LoaderCircle,
  Send,
  Radar,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { stepCategoryLabels, type StepCategory } from '@/lib/data'
import { TimelineStep } from '@/lib/event-mapper'
import { cn } from '@/lib/utils'

const categoryIcon: Record<StepCategory, LucideIcon> = {
  reasoning: Brain,
  retrieval: Database,
  action: Zap,
  notify: Send,
  monitor: Radar,
}

export function ExecutionTimeline({
  steps,
  isRunning,
  taskStatus,
}: {
  steps: TimelineStep[]
  isRunning: boolean
  taskStatus: string
}) {
  const doneCount = steps.filter((s) => s.status === 'done').length

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5">
            {isRunning ? (
              <>
                <span className="absolute inline-flex size-full animate-ai-pulse-ring rounded-full bg-primary" />
                <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
              </>
            ) : taskStatus === 'COMPLETED' ? (
              <span className="relative inline-flex size-2.5 rounded-full bg-resolved" />
            ) : (
              <span className="relative inline-flex size-2.5 rounded-full bg-high" />
            )}
          </span>
          <h2 className="text-sm font-semibold">Live Agent Execution Trace</h2>
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {doneCount} {doneCount === 1 ? 'action' : 'actions'} logged
        </span>
      </div>

      {steps.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <LoaderCircle className="mb-3 size-6 animate-spin text-primary" />
          <p className="text-sm font-medium text-foreground">
            Initializing autonomous agent loop...
          </p>
          <p className="text-xs text-muted-foreground">
            Contacting Gemini model and evaluating task instructions
          </p>
        </div>
      ) : (
        <ol className="relative">
          {steps.map((step, i) => (
            <TimelineRow
              key={step.id}
              step={step}
              icon={categoryIcon[step.category] || Zap}
              isLast={i === steps.length - 1}
            />
          ))}
        </ol>
      )}
    </div>
  )
}

function TimelineRow({
  step,
  icon: Icon,
  isLast,
}: {
  step: TimelineStep
  icon: LucideIcon
  isLast: boolean
}) {
  const done = step.status === 'done'
  const active = step.status === 'active'
  const pending = step.status === 'pending'

  return (
    <li className="animate-ai-rise">
      <div className="relative flex gap-4 pb-5">
        {/* connector */}
        {!isLast && (
          <span
            className={cn(
              'absolute top-9 left-[17px] h-[calc(100%-1.5rem)] w-px origin-top',
              done ? 'bg-primary/30' : 'bg-border',
            )}
            aria-hidden="true"
          />
        )}

        {/* node */}
        <div
          className={cn(
            'relative z-10 flex size-9 shrink-0 items-center justify-center rounded-xl ring-1 transition-colors',
            done && 'bg-primary/12 text-primary ring-primary/25',
            active && 'bg-primary/15 text-primary ring-primary/40',
            pending && 'bg-muted/60 text-muted-foreground ring-border',
          )}
        >
          {done ? (
            <Check className="size-4 text-resolved" />
          ) : active ? (
            <LoaderCircle className="size-4 animate-spin text-primary" />
          ) : (
            <Icon className="size-4 opacity-70" />
          )}
          {active && (
            <span className="absolute inset-0 rounded-xl ring-1 ring-primary/40 animate-ai-pulse-ring" />
          )}
        </div>

        {/* content */}
        <div
          className={cn(
            'min-w-0 flex-1 rounded-2xl border px-4 py-3 transition-colors',
            active
              ? 'ai-shimmer border-primary/30 bg-primary/[0.06]'
              : 'border-border/70 bg-card/40',
            pending && 'opacity-55',
          )}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                'rounded-md px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide uppercase',
                done || active
                  ? 'bg-primary/12 text-primary'
                  : 'bg-muted text-muted-foreground',
              )}
            >
              {stepCategoryLabels[step.category] || step.category}
            </span>
            <span className="text-sm font-medium">{step.title}</span>
            <span className="ml-auto font-mono text-[11px] text-muted-foreground">
              {step.timestamp}
            </span>
          </div>

          <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
            <code className="rounded bg-muted/70 px-1.5 py-0.5 font-mono text-[11px] text-foreground/80">
              {step.tool}
            </code>
            <span className="truncate">{step.action}</span>
          </div>

          {(done || active) && (
            <div
              className={cn(
                'mt-2 flex items-center gap-2 border-t border-border/50 pt-2 text-sm',
                active && 'text-primary',
              )}
            >
              <span
                className={cn(
                  'size-1.5 shrink-0 rounded-full',
                  active ? 'bg-primary animate-ai-blink' : 'bg-resolved',
                )}
              />
              <span className={cn(!active && 'text-foreground/90')}>
                {step.result}
              </span>
            </div>
          )}
        </div>
      </div>
    </li>
  )
}
