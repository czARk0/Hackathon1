'use client'

import {
  CalendarClock,
  CheckCircle2,
  History,
  Ticket,
  TriangleAlert,
  Wrench,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ExtractedHistory } from '@/lib/event-mapper'
import { AgentOutcome } from '@/lib/api'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium text-pretty">{value}</span>
    </div>
  )
}

export function HistoryCard({
  history,
}: {
  history: ExtractedHistory | null
}) {
  const incidentCount = history?.incidentCount ?? 0
  const incidents = history?.incidents ?? []
  const lastIncident = incidents[0]

  return (
    <Card className="gap-3">
      <CardHeader className="flex-row items-center gap-2">
        <History className="size-4 text-primary" />
        <CardTitle className="text-sm">Asset History (SQLite)</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col">
        <div className="mb-2 flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
          <span className="font-mono text-sm font-medium">
            {history?.asset || 'Projector'} · {history?.room || 'Lab 3'}
          </span>
          <span className="text-xs text-muted-foreground">
            Equipment Log
          </span>
        </div>
        <div className="divide-y divide-border/60">
          <Row
            label="Prior incidents"
            value={String(incidentCount)}
          />
          {lastIncident && (
            <>
              <Row
                label="Last issue"
                value={lastIncident.description || 'Display failure'}
              />
              <Row
                label="Last resolution"
                value={lastIncident.resolution || 'Resolved'}
              />
            </>
          )}
        </div>

        {incidentCount > 1 ? (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-high/10 px-3 py-2 text-xs font-medium text-high ring-1 ring-high/20">
            <TriangleAlert className="size-3.5" />
            Pattern: {incidentCount} repeated hardware failures
          </div>
        ) : (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
            <CheckCircle2 className="size-3.5 text-resolved" />
            Equipment history verified in database
          </div>
        )}
      </CardContent>
    </Card>
  )
}

const priorityConfig: Record<string, { badge: string; ring: string; dot: string }> = {
  HIGH: {
    badge: 'bg-high/15 text-high ring-high/30',
    ring: 'ring-high/25',
    dot: 'bg-high',
  },
  MEDIUM: {
    badge: 'bg-medium/15 text-medium ring-medium/30',
    ring: 'ring-medium/25',
    dot: 'bg-medium',
  },
  LOW: {
    badge: 'bg-low/15 text-low ring-low/30',
    ring: 'ring-low/25',
    dot: 'bg-low',
  },
  EVALUATING: {
    badge: 'bg-primary/15 text-primary ring-primary/30',
    ring: '',
    dot: 'bg-primary',
  },
}

export function PriorityCard({
  priority,
  reasons,
  isDeciding,
}: {
  priority: string | null
  reasons: string[]
  isDeciding: boolean
}) {
  const prio = (priority || 'EVALUATING').toUpperCase()
  const config = priorityConfig[prio] || priorityConfig.EVALUATING

  return (
    <Card className={`gap-3 ${config.ring}`}>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">Priority Assessment</CardTitle>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${config.badge}`}
        >
          {isDeciding && <span className="size-1.5 rounded-full bg-current animate-ai-blink" />}
          {prio} PRIORITY
        </span>
      </CardHeader>
      <CardContent>
        <p className="mb-2 text-xs text-muted-foreground">
          Single source of truth: backend agent determination
        </p>
        <ul className="flex flex-col gap-1.5">
          {reasons.length > 0 ? (
            reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className={`mt-1.5 size-1.5 shrink-0 rounded-full ${config.dot}`} />
                <span>{r}</span>
              </li>
            ))
          ) : (
            <li className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-muted-foreground" />
              <span>Analyzing incident records and deadline constraints...</span>
            </li>
          )}
        </ul>
      </CardContent>
    </Card>
  )
}

export function TicketCard({
  outcome,
  isRunning,
}: {
  outcome: AgentOutcome | null
  isRunning: boolean
}) {
  const ticketId = outcome?.ticket_id
  const notified = outcome?.technician_notified
  const reporter = outcome?.reporter

  return (
    <Card className="gap-3">
      <CardHeader className="flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Ticket className="size-4 text-primary" />
          <CardTitle className="text-sm">Maintenance Ticket</CardTitle>
        </div>
        <span className="font-mono text-sm font-medium text-primary">
          {ticketId ? `#${ticketId}` : isRunning ? 'Pending...' : '—'}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="divide-y divide-border/60">
          <Row label="Assigned role" value="AV Technician" />
          {reporter && (
            <Row label="Reported by" value={`${reporter.name} (${reporter.role})`} />
          )}
          <div className="flex items-center justify-between gap-3 py-1.5 text-sm">
            <span className="text-muted-foreground">Dispatch status</span>
            <span className="inline-flex items-center gap-1.5 font-medium text-primary">
              <Wrench className="size-3.5" />
              {notified
                ? 'Email notification delivered'
                : isRunning
                  ? 'Dispatching...'
                  : 'Awaiting manual follow-up'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-xs text-primary ring-1 ring-primary/20">
          <CalendarClock className="size-3.5" />
          Physical repair pending on-site
        </div>
      </CardContent>
    </Card>
  )
}
