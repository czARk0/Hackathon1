import { BackendEvent, AgentOutcome } from './api'

export type StepCategory = 'reasoning' | 'retrieval' | 'action' | 'notify' | 'monitor'
export type StepStatus = 'done' | 'active' | 'pending'

export type TimelineStep = {
  id: string
  category: StepCategory
  title: string
  tool: string
  action: string
  result: string
  timestamp: string
  status: StepStatus
}

export function formatEventTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch {
    return isoString
  }
}

export function mapBackendEventsToTimeline(
  events: BackendEvent[],
  isCompleted: boolean,
): TimelineStep[] {
  return events.map((ev, index) => {
    let category: StepCategory = 'reasoning'
    let title = 'Agent Operation'
    let tool = ev.tool || 'agent.internal'
    let action = 'Processing agent step'
    let resultText = ev.result || ''

    // Parse JSON result payload if applicable
    let parsedJson: any = null
    if (ev.result && (ev.result.startsWith('{') || ev.result.startsWith('['))) {
      try {
        parsedJson = JSON.parse(ev.result)
      } catch {
        // use raw string
      }
    }

    if (ev.event_type === 'memory_retrieval') {
      category = 'retrieval'
      title = 'Retrieving campus memory'
      tool = 'memory.retrieve'
      action = 'Searching historical task outcomes for room'
      if (parsedJson) {
        const count = parsedJson.count ?? (Array.isArray(parsedJson.memories) ? parsedJson.memories.length : 0)
        resultText = count > 0
          ? `Found ${count} prior task memory for this location`
          : 'No prior incident memory recorded for location'
      }
    } else if (ev.event_type === 'decision') {
      category = 'reasoning'
      tool = 'agent.decide'
      if (resultText.toLowerCase().includes('duplicate')) {
        title = 'Duplicate ticket check'
        action = 'Evaluating existing active tickets for location'
      } else {
        title = 'Determining priority'
        action = 'Evaluating incident history and urgency timeline'
      }
    } else if (ev.event_type === 'tool_call') {
      if (ev.tool === 'get_equipment_history') {
        category = 'retrieval'
        title = 'Checking equipment history'
        tool = 'equipment.getHistory'
        action = 'Querying incidents & maintenance records'
        if (parsedJson) {
          const count = parsedJson.incident_count ?? 0
          const descs = Array.isArray(parsedJson.incidents)
            ? parsedJson.incidents.map((inc: any) => inc.description).filter(Boolean).join(', ')
            : ''
          resultText = `${count} prior incident(s) found${descs ? ` (${descs})` : ''}`
        }
      } else if (ev.tool === 'create_maintenance_ticket') {
        category = 'action'
        title = 'Registering maintenance ticket'
        tool = 'tickets.create'
        action = 'Creating / updating ticket in SQLite database'
        if (parsedJson) {
          const tid = parsedJson.ticket_id
          const prio = parsedJson.priority ? ` · Priority ${parsedJson.priority}` : ''
          const dup = parsedJson.duplicate ? 'reused & escalated' : 'created'
          resultText = `Ticket #${tid} ${dup}${prio}`
        }
      } else if (ev.tool === 'notify_staff') {
        category = 'notify'
        title = 'Notifying AV technician'
        tool = 'notify.email'
        action = 'Dispatching email alert via Resend'
        if (ev.status === 'failed') {
          resultText = `Email notification failed: ${ev.result || 'Retry required'}`
        } else if (parsedJson) {
          resultText = `Email notification delivered to technician (msg: ${parsedJson.message_id || 'sent'})`
        } else {
          resultText = 'Email notification sent to technician'
        }
      } else if (ev.tool === 'verify_ticket') {
        category = 'monitor'
        title = 'Verifying database integrity'
        tool = 'db.verify'
        action = 'Validating ticket existence & notification status'
        if (parsedJson) {
          const ok = parsedJson.ticket_exists && parsedJson.priority_set && parsedJson.staff_notified
          resultText = ok
            ? 'All verification checks passed in database'
            : `Verification checks: ${JSON.stringify(parsedJson)}`
        }
      }
    } else if (ev.event_type === 'memory_save') {
      category = 'monitor'
      title = 'Persisting task memory'
      tool = 'memory.save'
      action = 'Writing task outcome to SQLite memory table'
      resultText = 'Outcome recorded in persistent agent memory'
    }

    const isLast = index === events.length - 1
    const status: StepStatus = ev.status === 'failed'
      ? 'done'
      : isLast && !isCompleted
        ? 'active'
        : 'done'

    return {
      id: `ev-${ev.id}`,
      category,
      title,
      tool,
      action,
      result: resultText,
      timestamp: formatEventTime(ev.timestamp),
      status,
    }
  })
}

export type ExtractedHistory = {
  asset: string
  room: string
  incidentCount: number
  incidents: Array<{ date?: string; description?: string; resolution?: string }>
}

export function extractEquipmentHistory(events: BackendEvent[]): ExtractedHistory | null {
  for (const ev of events) {
    if (ev.tool === 'get_equipment_history' && ev.result) {
      try {
        const data = JSON.parse(ev.result)
        return {
          asset: 'Projector',
          room: 'Lab 3',
          incidentCount: data.incident_count || 0,
          incidents: Array.isArray(data.incidents) ? data.incidents : [],
        }
      } catch {
        // ignore parse error
      }
    }
  }
  return null
}
