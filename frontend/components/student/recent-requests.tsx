'use client'

import { ArrowUpRight, Inbox, MapPin } from 'lucide-react'
import { PriorityDot } from '@/components/priority-badge'
import { StoredRequest } from '@/lib/recent-requests'
import { cn } from '@/lib/utils'

export function RecentRequests({
  requests = [],
  onSelectRequest,
}: {
  requests?: StoredRequest[]
  onSelectRequest?: (req: StoredRequest) => void
}) {
  return (
    <section aria-labelledby="recent-heading" className="w-full">
      <div className="mb-3 flex items-center justify-between">
        <h2
          id="recent-heading"
          className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
        >
          Your recent requests
        </h2>
        <span className="font-mono text-xs text-muted-foreground/70">
          {requests.length} {requests.length === 1 ? 'tracked' : 'tracked'}
        </span>
      </div>

      {requests.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border/70 bg-card/30 px-6 py-8 text-center">
          <Inbox className="mb-2 size-6 text-muted-foreground/50" />
          <p className="text-sm font-medium text-foreground/80">
            No recent requests submitted yet
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Issues you report to Campus Commander will be logged and tracked here with live status updates.
          </p>
        </div>
      ) : (
        <ul className="grid gap-2 sm:grid-cols-3">
          {requests.map((r) => {
            const isCompleted = r.status === 'COMPLETED'
            const isFailed = r.status === 'NOTIFICATION_FAILED' || r.status === 'FAILED'
            const statusLabel = isCompleted
              ? 'Dispatched'
              : isFailed
                ? 'Awaiting Follow-up'
                : 'Executing'
            const statusClass = isCompleted
              ? 'text-resolved'
              : isFailed
                ? 'text-high'
                : 'text-primary'

            const normPriority = (r.priority || 'medium').toLowerCase() as 'high' | 'medium' | 'low' | 'resolved'
            const priorityTextColor = normPriority === 'high'
              ? 'text-high'
              : normPriority === 'medium'
                ? 'text-medium'
                : 'text-low'

            return (
              <li key={r.taskId}>
                <button
                  type="button"
                  onClick={() => onSelectRequest?.(r)}
                  className="group flex h-full w-full flex-col gap-3 rounded-2xl border border-border/70 bg-card/50 p-4 text-left transition-all hover:border-primary/40 hover:bg-card/80"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-mono text-xs font-medium text-foreground/80 group-hover:text-primary">
                      {r.ticketId ? `Ticket #${r.ticketId}` : `Task #${r.taskId}`}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <span className={cn('text-[10px] font-semibold uppercase tracking-wider', priorityTextColor)}>
                        {normPriority}
                      </span>
                      <PriorityDot priority={normPriority} />
                      <ArrowUpRight className="size-3 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                    </div>
                  </div>
                  <div className="line-clamp-2 text-sm font-medium text-pretty text-foreground">
                    {r.goal}
                  </div>
                  <div className="mt-auto flex items-center gap-1.5 text-xs text-muted-foreground">
                    <MapPin className="size-3.5 text-primary" />
                    <span className="truncate">{r.room}</span>
                  </div>
                  <div className="flex items-center justify-between border-t border-border/60 pt-2.5 w-full">
                    <span className={cn('text-xs font-medium', statusClass)}>
                      {statusLabel}
                    </span>
                    <span className="text-xs text-muted-foreground/70">
                      {r.timeFormatted}
                    </span>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
