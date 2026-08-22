'use client'

import { ArrowLeft, CheckCircle2, MapPin, Sparkles, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ExecutionTimeline } from '@/components/student/execution-timeline'
import {
  HistoryCard,
  PriorityCard,
  TicketCard,
} from '@/components/student/side-cards'
import { LifecycleStepper } from '@/components/student/lifecycle-stepper'
import { AgentOutcome, BackendEvent } from '@/lib/api'
import {
  extractEquipmentHistory,
  mapBackendEventsToTimeline,
} from '@/lib/event-mapper'

export function AgentExecution({
  query,
  taskId,
  events,
  taskStatus,
  outcome,
  reporterName,
  reporterRole,
  onReset,
}: {
  query: string
  taskId: number
  events: BackendEvent[]
  taskStatus: string
  outcome: AgentOutcome | null
  reporterName?: string
  reporterRole?: string
  onReset: () => void
}) {
  const isRunning = taskStatus === 'RUNNING' || taskStatus === 'running'
  const isCompleted = taskStatus === 'COMPLETED'
  const isNotificationFailed =
    taskStatus === 'NOTIFICATION_FAILED' || taskStatus === 'NEEDS_HUMAN_INTERVENTION'

  const timelineSteps = mapBackendEventsToTimeline(events, isCompleted)
  const equipmentHistory = extractEquipmentHistory(events)

  // SINGLE SOURCE OF TRUTH: Backend outcome priority
  let currentPriority: string | null = null
  let priorityReasons: string[] = []

  if (outcome?.priority) {
    currentPriority = String(outcome.priority).toUpperCase()
  } else {
    // While task is executing before outcome is received, check real ticket event or decision event
    const ticketEvent = events.find((e) => e.tool === 'create_maintenance_ticket')
    if (ticketEvent?.result) {
      try {
        const parsed = JSON.parse(ticketEvent.result)
        if (parsed.priority) {
          currentPriority = String(parsed.priority).toUpperCase()
        }
      } catch {}
    }

    if (!currentPriority) {
      const decisionEvent = events.find((e) => e.event_type === 'decision')
      if (decisionEvent?.result) {
        const match = decisionEvent.result.match(/\b(HIGH|MEDIUM|LOW)\b/i)
        if (match) {
          currentPriority = match[1].toUpperCase()
        }
      }
    }
  }

  // Populate reasons from decision event or equipment history
  const decisionEvent = events.find((e) => e.event_type === 'decision')
  if (decisionEvent?.result) {
    priorityReasons = [decisionEvent.result]
  }

  if (equipmentHistory && equipmentHistory.incidentCount > 0) {
    priorityReasons.push(`${equipmentHistory.incidentCount} previous incident(s) recorded in SQLite`)
  }

  const isDeciding = isRunning && !currentPriority

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-8">
      <div className="mb-5 flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={onReset}
          className="text-muted-foreground"
        >
          <ArrowLeft className="size-4" />
          New request
        </Button>

        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">
            Task #{taskId}
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
              isCompleted
                ? 'bg-resolved/15 text-resolved ring-1 ring-resolved/30'
                : isNotificationFailed
                  ? 'bg-high/15 text-high ring-1 ring-high/30'
                  : 'bg-primary/15 text-primary ring-1 ring-primary/30'
            }`}
          >
            {taskStatus}
          </span>
        </div>
      </div>

      {/* User message -> Agent acknowledgment banner */}
      <div className="mb-6 overflow-hidden rounded-2xl border border-border/70 bg-card/60">
        <div className="flex items-start gap-3 border-b border-border/60 px-5 py-4">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold">
            {reporterName ? reporterName.charAt(0) : 'U'}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-xs text-muted-foreground">
                Reported by {reporterName || 'Student'} {reporterRole ? `(${reporterRole})` : ''}
              </p>
            </div>
            <p className="text-pretty text-base font-medium">
              &ldquo;{query}&rdquo;
            </p>
          </div>
        </div>

        <div
          className={`flex items-start gap-3 px-5 py-3 ${
            isNotificationFailed
              ? 'bg-high/[0.08]'
              : 'bg-primary/[0.05]'
          }`}
        >
          <span
            className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full ring-1 ${
              isCompleted
                ? 'bg-resolved/15 text-resolved ring-resolved/25'
                : isNotificationFailed
                  ? 'bg-high/15 text-high ring-high/25'
                  : 'bg-primary/15 text-primary ring-primary/25'
            }`}
          >
            {isCompleted ? (
              <CheckCircle2 className="size-4" />
            ) : isNotificationFailed ? (
              <TriangleAlert className="size-4" />
            ) : (
              <Sparkles className="size-4" />
            )}
          </span>
          <div className="flex flex-1 flex-wrap items-center gap-x-3 gap-y-1">
            <p className="text-sm leading-relaxed">
              {outcome?.message ? (
                <span>{outcome.message}</span>
              ) : isRunning ? (
                <span>
                  <strong className="font-medium">Campus Commander</strong> took
                  over — autonomously assessing incident history, assigning priority,
                  and dispatching the technician.
                </span>
              ) : (
                <span>Autonomous loop ended with status: {taskStatus}</span>
              )}
            </p>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-card px-2.5 py-1 text-xs text-muted-foreground ring-1 ring-border">
              <MapPin className="size-3.5 text-primary" />
              Lab 3 · Campus Facility
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="rounded-2xl border border-border/70 bg-card/40 p-5">
          <ExecutionTimeline
            steps={timelineSteps}
            isRunning={isRunning}
            taskStatus={taskStatus}
          />
        </div>

        <aside className="flex flex-col gap-4">
          <PriorityCard
            priority={currentPriority}
            reasons={priorityReasons}
            isDeciding={isDeciding}
          />
          <TicketCard outcome={outcome} isRunning={isRunning} />
          <HistoryCard history={equipmentHistory} />
        </aside>
      </div>

      <div className="mt-6">
        <LifecycleStepper events={events} isCompleted={isCompleted} />
      </div>
    </div>
  )
}
