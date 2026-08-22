'use client'

import { useEffect, useRef, useState } from 'react'
import { Landing } from '@/components/student/landing'
import { AgentExecution } from '@/components/student/agent-execution'
import {
  AgentOutcome,
  BackendEvent,
  getReporters,
  getTaskEvents,
  getTaskStatus,
  Reporter,
  runAgent,
} from '@/lib/api'
import {
  extractRoomFromGoal,
  getStoredRequests,
  saveStoredRequest,
  StoredRequest,
  updateStoredRequest,
} from '@/lib/recent-requests'
import { LoaderCircle, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type Phase = 'idle' | 'submitting' | 'running' | 'error'

const TERMINAL_STATUSES = new Set([
  'COMPLETED',
  'FAILED',
  'NOTIFICATION_FAILED',
  'NEEDS_HUMAN_INTERVENTION',
])

export function StudentApp() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [reporters, setReporters] = useState<Reporter[]>([])
  const [selectedReporterId, setSelectedReporterId] = useState<number>(1)
  const [query, setQuery] = useState('')
  const [taskId, setTaskId] = useState<number | null>(null)
  const [taskStatus, setTaskStatus] = useState<string>('RUNNING')
  const [events, setEvents] = useState<BackendEvent[]>([])
  const [outcome, setOutcome] = useState<AgentOutcome | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [storedRequests, setStoredRequests] = useState<StoredRequest[]>([])

  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  // 1. Fetch live reporters & load stored requests on mount
  useEffect(() => {
    let mounted = true
    getReporters()
      .then((data) => {
        if (mounted && data && data.length > 0) {
          setReporters(data)
          setSelectedReporterId(data[0].id)
        }
      })
      .catch((err) => {
        console.error('[StudentApp] Failed to load reporters:', err)
        if (mounted) {
          setReporters([
            { id: 1, name: 'Arjun Reddy', role: 'Student', email: 'student1@example.com' },
          ])
          setSelectedReporterId(1)
        }
      })

    // Load initial stored requests
    if (mounted) {
      setStoredRequests(getStoredRequests())
    }

    return () => {
      mounted = false
    }
  }, [])

  // 2. Clear polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // 3. Submit handler: POST /agent/run
  async function handleSubmit(value: string, reporterId: number) {
    setQuery(value)
    setErrorMessage(null)
    setPhase('submitting')
    setEvents([])
    setOutcome(null)

    try {
      const res = await runAgent(value, reporterId)
      const newTaskId = res.task_id
      setTaskId(newTaskId)
      setTaskStatus('RUNNING')
      setPhase('running')

      // Record in persistent browser history immediately
      const initialRecord: StoredRequest = {
        taskId: newTaskId,
        ticketId: null,
        goal: value,
        room: extractRoomFromGoal(value),
        status: 'RUNNING',
        priority: 'medium',
        technicianNotified: false,
        timestamp: new Date().toISOString(),
        timeFormatted: 'Just now',
      }
      saveStoredRequest(initialRecord)
      setStoredRequests(getStoredRequests())

      // Start live polling loop
      startPolling(newTaskId)
    } catch (err: any) {
      console.error('[StudentApp] runAgent error:', err)
      setErrorMessage(err.message || 'Failed to contact Campus Commander backend')
      setPhase('error')
    }
  }

  // 4. Polling loop for events & task status
  function startPolling(id: number) {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
    }

    const poll = async () => {
      try {
        // Poll events
        const evList = await getTaskEvents(id)
        setEvents(evList)

        // Poll task status & outcome
        const taskData = await getTaskStatus(id)
        const currentStatus = taskData.status || 'RUNNING'
        setTaskStatus(currentStatus)

        if (taskData.outcome) {
          setOutcome(taskData.outcome)

          // Update recent request record with the backend's exact single source of truth priority
          const backendPriority = (taskData.outcome.priority || 'MEDIUM').toLowerCase() as 'high' | 'medium' | 'low'
          updateStoredRequest(id, {
            ticketId: taskData.outcome.ticket_id,
            status: taskData.outcome.status || currentStatus,
            priority: backendPriority,
            technicianNotified: taskData.outcome.technician_notified,
          })
          setStoredRequests(getStoredRequests())
        }

        // Stop polling if terminal status is reached
        if (TERMINAL_STATUSES.has(currentStatus.toUpperCase())) {
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        }
      } catch (err) {
        console.warn('[StudentApp] polling warning:', err)
      }
    }

    // First immediate poll
    poll()
    // Recurring poll every 650ms
    pollingRef.current = setInterval(poll, 650)
  }

  // 5. Select a previous request from recent requests list
  function handleSelectRecentRequest(req: StoredRequest) {
    setQuery(req.goal)
    setTaskId(req.taskId)
    setTaskStatus(req.status)
    setPhase('running')
    setEvents([])
    setOutcome(null)
    startPolling(req.taskId)
  }

  function handleReset() {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
    setPhase('idle')
    setQuery('')
    setTaskId(null)
    setEvents([])
    setOutcome(null)
    setErrorMessage(null)
    setStoredRequests(getStoredRequests())
  }

  const selectedReporter = reporters.find((r) => r.id === selectedReporterId)

  if (phase === 'idle') {
    return (
      <Landing
        onSubmit={handleSubmit}
        reporters={reporters}
        selectedReporterId={selectedReporterId}
        onSelectReporter={setSelectedReporterId}
        requests={storedRequests}
        onSelectRequest={handleSelectRecentRequest}
      />
    )
  }

  if (phase === 'submitting') {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-5">
        <div className="relative mb-6 flex size-16 items-center justify-center">
          <LoaderCircle className="size-8 animate-spin text-primary" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">
          Submitting request to Campus Commander...
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Establishing background task and initializing Gemini planning agent
        </p>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-5">
        <div className="mb-4 flex size-14 items-center justify-center rounded-full bg-high/15 text-high ring-1 ring-high/30">
          <TriangleAlert className="size-6" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">
          Unable to start agent execution
        </h2>
        <p className="mt-2 max-w-md text-center text-sm text-muted-foreground">
          {errorMessage || 'An error occurred while connecting to the backend.'}
        </p>
        <p className="mt-1 text-xs text-muted-foreground/80">
          Ensure FastAPI backend is running at http://127.0.0.1:8000
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={handleReset}
          className="mt-6"
        >
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <AgentExecution
      query={query}
      taskId={taskId || 1}
      events={events}
      taskStatus={taskStatus}
      outcome={outcome}
      reporterName={selectedReporter?.name}
      reporterRole={selectedReporter?.role}
      onReset={handleReset}
    />
  )
}
