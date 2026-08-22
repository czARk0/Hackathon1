export type StoredRequest = {
  taskId: number
  ticketId: number | null
  goal: string
  room: string
  status: string
  priority: 'high' | 'medium' | 'low' | 'resolved'
  technicianNotified: boolean
  timestamp: string
  timeFormatted: string
}

const STORAGE_KEY = 'campus_commander_recent_requests'

export function extractRoomFromGoal(goal: string): string {
  const g = goal.toLowerCase()
  if (g.includes('lab 3')) return 'Lab 3'
  if (g.includes('lab 1')) return 'Lab 1'
  if (g.includes('lab 2')) return 'Lab 2'
  if (g.includes('library')) return 'Library'
  if (g.includes('hostel block c')) return 'Hostel Block C'
  if (g.includes('lecture hall')) return 'Lecture Hall'
  return 'Campus Facility'
}

export function formatRequestTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return 'Recently'
    const now = new Date()
    const diffMin = Math.round((now.getTime() - d.getTime()) / 60000)
    if (diffMin < 1) return 'Just now'
    if (diffMin < 60) return `${diffMin}m ago`
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return 'Recently'
  }
}

export function getStoredRequests(): StoredRequest[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.map((item) => ({
      ...item,
      timeFormatted: formatRequestTime(item.timestamp),
    }))
  } catch {
    return []
  }
}

export function saveStoredRequest(req: StoredRequest): void {
  if (typeof window === 'undefined') return
  try {
    const current = getStoredRequests()
    // Avoid duplicate taskIds
    const filtered = current.filter((r) => r.taskId !== req.taskId)
    const updated = [req, ...filtered].slice(0, 10)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch (err) {
    console.error('Failed to save recent request to localStorage:', err)
  }
}

export function updateStoredRequest(
  taskId: number,
  updates: Partial<StoredRequest>,
): void {
  if (typeof window === 'undefined') return
  try {
    const current = getStoredRequests()
    const updated = current.map((r) => {
      if (r.taskId === taskId) {
        return {
          ...r,
          ...updates,
          priority: updates.priority ? (updates.priority.toLowerCase() as any) : r.priority,
        }
      }
      return r
    })
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch (err) {
    console.error('Failed to update recent request in localStorage:', err)
  }
}
