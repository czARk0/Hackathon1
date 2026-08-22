'use client'

import { useMemo, useState } from 'react'
import { ListFilter } from 'lucide-react'
import { adminIssues, type AdminIssue } from '@/lib/data'
import { PriorityBadge } from '@/components/priority-badge'
import { cn } from '@/lib/utils'

const priorityRank: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
  resolved: 3,
}

const flagStyles: Record<string, string> = {
  escalated: 'bg-high/15 text-high ring-high/30',
  repeated: 'bg-medium/15 text-medium ring-medium/30',
  overdue: 'bg-low/15 text-low ring-low/30',
}

type Filter = 'all' | 'escalated' | 'repeated' | 'overdue'
const filters: Filter[] = ['all', 'escalated', 'repeated', 'overdue']

export function PriorityTable() {
  const [filter, setFilter] = useState<Filter>('all')

  const rows = useMemo(() => {
    const list =
      filter === 'all'
        ? adminIssues
        : adminIssues.filter((i) => i.flags.includes(filter as never))
    return [...list].sort(
      (a, b) => priorityRank[a.priority] - priorityRank[b.priority],
    )
  }, [filter])

  return (
    <div className="flex h-full flex-col rounded-2xl bg-card/60 ring-1 ring-foreground/10">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <ListFilter className="size-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Priority issue queue</h2>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-border/70 bg-background/40 p-0.5">
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-medium capitalize transition-colors',
                filter === f
                  ? 'bg-secondary text-secondary-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-xs text-muted-foreground">
              <th className="px-4 py-2 font-medium">Issue</th>
              <th className="px-4 py-2 font-medium">Location</th>
              <th className="px-4 py-2 font-medium">Priority</th>
              <th className="hidden px-4 py-2 font-medium md:table-cell">Team</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="hidden px-4 py-2 font-medium lg:table-cell">Age</th>
              <th className="px-4 py-2 font-medium">Ticket</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((issue) => (
              <IssueRow key={issue.ticket} issue={issue} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function IssueRow({ issue }: { issue: AdminIssue }) {
  const escalated = issue.flags.includes('escalated')
  return (
    <tr className="border-t border-border/50 transition-colors hover:bg-muted/30">
      <td className="max-w-[15rem] px-4 py-3">
        <div className="flex items-center gap-2">
          {escalated && (
            <span className="h-4 w-1 shrink-0 rounded-full bg-high" />
          )}
          <span className="truncate font-medium text-pretty">{issue.issue}</span>
        </div>
        {issue.flags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {issue.flags.map((f) => (
              <span
                key={f}
                className={cn(
                  'rounded px-1.5 py-0.5 text-[10px] font-medium capitalize ring-1 ring-inset',
                  flagStyles[f],
                )}
              >
                {f}
              </span>
            ))}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-muted-foreground">{issue.location}</td>
      <td className="px-4 py-3">
        <PriorityBadge priority={issue.priority} />
      </td>
      <td className="hidden px-4 py-3 text-muted-foreground md:table-cell">
        {issue.team}
      </td>
      <td className="px-4 py-3">
        <span
          className={cn(
            'text-xs font-medium',
            issue.statusKind === 'escalated'
              ? 'text-high'
              : issue.statusKind === 'in-progress' ||
                  issue.statusKind === 'assigned'
                ? 'text-primary'
                : issue.statusKind === 'resolved'
                  ? 'text-resolved'
                  : 'text-muted-foreground',
          )}
        >
          {issue.status}
        </span>
      </td>
      <td className="hidden px-4 py-3 font-mono text-xs text-muted-foreground lg:table-cell">
        {issue.age}
      </td>
      <td className="px-4 py-3 font-mono text-xs text-primary">
        {issue.ticket}
      </td>
    </tr>
  )
}
