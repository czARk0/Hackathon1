/**
 * api.ts -- Live Backend API Client for Campus Commander
 *
 * Connects directly to the FastAPI backend running at http://127.0.0.1:8000
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export type Reporter = {
  id: number
  name: string
  role: string
  email: string
}

export type RunResponse = {
  task_id: number
  status: string
}

export type VerificationResult = {
  ticket_exists: boolean
  priority_set: boolean
  staff_notified: boolean
}

export type AgentOutcome = {
  status: string
  ticket_id: number | null
  priority: string | null
  technician_notified: boolean
  reporter?: {
    id: number
    name: string
    role: string
  } | null
  message: string
  steps_executed?: number
  tool_calls_made?: number
  verification?: VerificationResult
}

export type TaskStatusResponse = {
  task_id: number
  status: string
  outcome: AgentOutcome | null
}

export type BackendEvent = {
  id: number
  event_type: string // 'memory_retrieval' | 'tool_call' | 'decision' | 'memory_save'
  tool: string | null // 'get_equipment_history' | 'create_maintenance_ticket' | 'notify_staff' | 'verify_ticket' | 'retrieve_memories' | 'save_memory'
  status: string // 'success' | 'failed'
  result: string | null
  timestamp: string
}

export type TaskEventsResponse = {
  task_id: number
  events: BackendEvent[]
}

export type ImageAnalysis = {
  issue?: string
  equipment?: string
  visible_damage?: string
  location?: string | null
  confidence?: number
}

export type AnalyzeImageResponse = {
  analysis: ImageAnalysis
  combined_goal: string
}

/**
 * Fetch available campus reporters from GET /reporters
 */
export async function getReporters(): Promise<Reporter[]> {
  const res = await fetch(`${API_BASE}/reporters`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch reporters: HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * Submit goal and reporter_id to POST /agent/run
 */
export async function runAgent(
  goal: string,
  reporter_id: number,
): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, reporter_id }),
  })
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(`Failed to start agent task: ${errorDetail}`)
  }
  return res.json()
}

/**
 * Analyze an uploaded facility photo using backend Gemini Vision
 */
export async function analyzeImage(
  file: File,
  userText?: string,
): Promise<AnalyzeImageResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (userText && userText.trim()) {
    formData.append('user_text', userText.trim())
  }

  const res = await fetch(`${API_BASE}/agent/analyze-image`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) {
        errorDetail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {}
    throw new Error(`Image analysis failed: ${errorDetail}`)
  }

  return res.json()
}

/**
 * Poll task status and outcome from GET /agent/task/{task_id}
 */
export async function getTaskStatus(taskId: number): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE}/agent/task/${taskId}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch task #${taskId}: HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * Poll execution events from GET /agent/task/{task_id}/events
 */
export async function getTaskEvents(taskId: number): Promise<BackendEvent[]> {
  const res = await fetch(`${API_BASE}/agent/task/${taskId}/events`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch events for task #${taskId}: HTTP ${res.status}`)
  }
  const data: TaskEventsResponse = await res.json()
  return data.events || []
}
