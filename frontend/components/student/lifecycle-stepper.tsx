'use client'

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BackendEvent } from '@/lib/api'

export function LifecycleStepper({
  events,
  isCompleted,
}: {
  events: BackendEvent[]
  isCompleted: boolean
}) {
  const hasHistory = events.some((e) => e.tool === 'get_equipment_history' || e.event_type === 'decision')
  const hasTicket = events.some((e) => e.tool === 'create_maintenance_ticket')
  const hasNotify = events.some((e) => e.tool === 'notify_staff')
  const hasVerify = events.some((e) => e.tool === 'verify_ticket')

  const stages = [
    {
      key: 'reported',
      label: 'Reported',
      state: 'done',
    },
    {
      key: 'analyzed',
      label: 'Triaged & Prioritized',
      state: hasHistory ? 'done' : 'current',
    },
    {
      key: 'ticket',
      label: 'Ticket Created',
      state: hasTicket ? 'done' : hasHistory ? 'current' : 'upcoming',
    },
    {
      key: 'dispatched',
      label: 'Technician Dispatched',
      state: hasNotify ? 'done' : hasTicket ? 'current' : 'upcoming',
    },
    {
      key: 'verified',
      label: 'Database Verified',
      state: hasVerify ? 'done' : hasNotify ? 'current' : 'upcoming',
    },
    {
      key: 'repair',
      label: 'Physical Repair Pending',
      state: isCompleted ? 'current' : 'upcoming',
    },
  ]

  return (
    <div className="rounded-2xl border border-border/70 bg-card/40 p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Autonomous Lifecycle Progress</h3>
        <span className="font-mono text-xs text-muted-foreground">
          {isCompleted ? 'Loop Completed' : 'Executing Live'}
        </span>
      </div>
      <ol className="flex flex-col gap-0 sm:flex-row sm:items-start sm:gap-0">
        {stages.map((stage, i) => {
          const done = stage.state === 'done'
          const current = stage.state === 'current'
          const last = i === stages.length - 1
          return (
            <li
              key={stage.key}
              className="flex flex-1 gap-3 sm:flex-col sm:items-center sm:gap-2 sm:text-center"
            >
              <div className="flex flex-col items-center sm:w-full sm:flex-row">
                <span
                  className={cn(
                    'flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium ring-1 transition-colors sm:mx-auto',
                    done && 'bg-primary/15 text-primary ring-primary/30',
                    current &&
                      'bg-primary text-primary-foreground ring-primary',
                    !done && !current && 'bg-muted text-muted-foreground ring-border',
                  )}
                >
                  {done ? (
                    <Check className="size-3.5" />
                  ) : current ? (
                    <span className="size-2 rounded-full bg-primary-foreground animate-ai-blink" />
                  ) : (
                    i + 1
                  )}
                </span>
                {/* connector */}
                {!last && (
                  <span
                    className={cn(
                      'my-1 h-6 w-px sm:my-0 sm:h-px sm:w-full',
                      done ? 'bg-primary/40' : 'bg-border',
                    )}
                    aria-hidden="true"
                  />
                )}
              </div>
              <span
                className={cn(
                  'pb-4 text-xs sm:pb-0',
                  current
                    ? 'font-medium text-foreground'
                    : done
                      ? 'text-foreground/80'
                      : 'text-muted-foreground',
                )}
              >
                {stage.label}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
