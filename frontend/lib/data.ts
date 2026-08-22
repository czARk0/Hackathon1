export type Priority = 'high' | 'medium' | 'low' | 'resolved'

export type IssueStatus =
  | 'analyzing'
  | 'assigned'
  | 'in-progress'
  | 'awaiting'
  | 'escalated'
  | 'resolved'

export type RecentRequest = {
  id: string
  ticket: string
  issue: string
  location: string
  status: string
  statusKind: IssueStatus
  priority: Priority
  time: string
}

export const recentRequests: RecentRequest[] = [
  {
    id: 'r1',
    ticket: 'CC-1042',
    issue: 'Projector flickering',
    location: 'Lecture Hall B',
    status: 'Technician working',
    statusKind: 'in-progress',
    priority: 'medium',
    time: '2h ago',
  },
  {
    id: 'r2',
    ticket: 'CC-1039',
    issue: 'AC not cooling',
    location: 'Library — Level 2',
    status: 'Resolved',
    statusKind: 'resolved',
    priority: 'resolved',
    time: 'Yesterday',
  },
  {
    id: 'r3',
    ticket: 'CC-1031',
    issue: 'Wi-Fi dropping',
    location: 'Hostel Block C',
    status: 'Awaiting confirmation',
    statusKind: 'awaiting',
    priority: 'low',
    time: '2 days ago',
  },
]

/* ---------------- Agent Execution ---------------- */

export type StepStatus = 'done' | 'active' | 'pending'
export type StepCategory =
  | 'reasoning'
  | 'retrieval'
  | 'action'
  | 'notify'
  | 'monitor'

export type ExecutionStep = {
  id: string
  category: StepCategory
  title: string
  tool: string
  action: string
  result: string
  timestamp: string
  status: StepStatus
}

export const executionSteps: ExecutionStep[] = [
  {
    id: 's1',
    category: 'reasoning',
    title: 'Understanding request',
    tool: 'intent.classify',
    action: 'Parsing natural-language report',
    result: 'Hardware fault · desktop computer · Lab 3',
    timestamp: '10:42:01',
    status: 'done',
  },
  {
    id: 's2',
    category: 'reasoning',
    title: 'Locating on campus map',
    tool: 'campus.resolveLocation',
    action: 'Matching "Lab 3" to campus directory',
    result: 'Computer Lab 3 · Engineering Block · Floor 3',
    timestamp: '10:42:02',
    status: 'done',
  },
  {
    id: 's3',
    category: 'retrieval',
    title: 'Identifying asset',
    tool: 'assets.lookup',
    action: 'Matching asset PC-03-17...',
    result: 'Asset PC-03-17 confirmed (Dell OptiPlex)',
    timestamp: '10:42:03',
    status: 'done',
  },
  {
    id: 's4',
    category: 'retrieval',
    title: 'Searching incident history',
    tool: 'incidents.search',
    action: 'Searching incident history...',
    result: '3 previous incidents found · repeated failure pattern',
    timestamp: '10:42:04',
    status: 'done',
  },
  {
    id: 's5',
    category: 'reasoning',
    title: 'Identifying prior resolver',
    tool: 'incidents.analyze',
    action: 'Reviewing last resolution record',
    result: 'Previous resolver identified: IT Support',
    timestamp: '10:42:05',
    status: 'done',
  },
  {
    id: 's6',
    category: 'action',
    title: 'Creating support ticket',
    tool: 'tickets.create',
    action: 'Creating ticket CC-1048...',
    result: 'Ticket CC-1048 created · priority HIGH',
    timestamp: '10:42:06',
    status: 'done',
  },
  {
    id: 's7',
    category: 'action',
    title: 'Selecting responsible team',
    tool: 'routing.assign',
    action: 'Matching skills & prior resolver',
    result: 'Assigned to IT Support · A. Mehta on shift',
    timestamp: '10:42:07',
    status: 'done',
  },
  {
    id: 's8',
    category: 'notify',
    title: 'Sending notification',
    tool: 'notify.dispatch',
    action: 'Notifying assigned team',
    result: 'Notification sent · SMS + email delivered',
    timestamp: '10:42:08',
    status: 'done',
  },
  {
    id: 's9',
    category: 'monitor',
    title: 'Scheduling follow-up',
    tool: 'scheduler.set',
    action: 'Follow-up scheduled...',
    result: 'Auto follow-up set for 30 minutes',
    timestamp: '10:42:09',
    status: 'active',
  },
  {
    id: 's10',
    category: 'monitor',
    title: 'Monitoring resolution',
    tool: 'monitor.track',
    action: 'Awaiting technician update',
    result: 'Tracking · will verify with reporter',
    timestamp: '—',
    status: 'pending',
  },
]

export const stepCategoryLabels: Record<StepCategory, string> = {
  reasoning: 'Reasoning',
  retrieval: 'Retrieval',
  action: 'Action',
  notify: 'Notify',
  monitor: 'Monitor',
}

/* ---------------- Side cards ---------------- */

export const assetHistory = {
  asset: 'PC-03-17',
  model: 'Dell OptiPlex 7090',
  lastIssue: 'Power supply failure',
  lastRepaired: '18 Aug 2026',
  resolvedBy: 'IT Support',
  previousIncidents: 3,
  pattern: 'Repeated failure',
}

export const priorityCard = {
  level: 'HIGH' as const,
  reasons: [
    'Multiple previous incidents',
    'Repeated hardware failure',
    'Active teaching lab affected',
  ],
}

export const ticketCard = {
  id: 'CC-1048',
  assignedTo: 'IT Support',
  status: 'Technician notified',
  nextFollowUp: '30 minutes',
}

export type LifecycleStage = {
  key: string
  label: string
  state: 'done' | 'current' | 'upcoming'
}

export const lifecycle: LifecycleStage[] = [
  { key: 'reported', label: 'Reported', state: 'done' },
  { key: 'analyzed', label: 'Analyzed', state: 'done' },
  { key: 'assigned', label: 'Assigned', state: 'done' },
  { key: 'working', label: 'Technician working', state: 'current' },
  { key: 'resolved', label: 'Resolved', state: 'upcoming' },
  { key: 'verify', label: 'User verification', state: 'upcoming' },
  { key: 'closed', label: 'Closed', state: 'upcoming' },
]

/* ---------------- Admin ---------------- */

export type Metric = {
  label: string
  value: string
  delta?: string
  trend?: 'up' | 'down' | 'flat'
  tone?: 'default' | 'high' | 'resolved'
}

export const adminMetrics: Metric[] = [
  { label: 'Active issues', value: '28', delta: '+4 today', trend: 'up' },
  { label: 'High priority', value: '6', delta: '2 escalated', trend: 'up', tone: 'high' },
  { label: 'Awaiting resolution', value: '11', delta: '3 overdue', trend: 'flat' },
  { label: 'Resolved today', value: '19', delta: '+31%', trend: 'up', tone: 'resolved' },
  { label: 'Resolution rate', value: '94%', delta: '7d avg', trend: 'up', tone: 'resolved' },
]

export type AdminIssue = {
  ticket: string
  issue: string
  location: string
  priority: Priority
  team: string
  status: string
  statusKind: IssueStatus
  flags: Array<'escalated' | 'repeated' | 'overdue'>
  age: string
}

export const adminIssues: AdminIssue[] = [
  {
    ticket: 'CC-1048',
    issue: 'PC not working (PC-03-17)',
    location: 'Computer Lab 3',
    priority: 'high',
    team: 'IT Support',
    status: 'Technician notified',
    statusKind: 'assigned',
    flags: ['repeated'],
    age: '3m',
  },
  {
    ticket: 'CC-1044',
    issue: 'Power outage — full wing',
    location: 'Science Block',
    priority: 'high',
    team: 'Facilities',
    status: 'Escalated to supervisor',
    statusKind: 'escalated',
    flags: ['escalated', 'overdue'],
    age: '2h 40m',
  },
  {
    ticket: 'CC-1041',
    issue: 'Water leak near servers',
    location: 'Admin Block',
    priority: 'high',
    team: 'Facilities',
    status: 'Technician working',
    statusKind: 'in-progress',
    flags: ['escalated'],
    age: '1h 05m',
  },
  {
    ticket: 'CC-1042',
    issue: 'Projector flickering',
    location: 'Lecture Hall B',
    priority: 'medium',
    team: 'AV Team',
    status: 'Technician working',
    statusKind: 'in-progress',
    flags: [],
    age: '2h',
  },
  {
    ticket: 'CC-1037',
    issue: 'AC not cooling',
    location: 'Library — Level 2',
    priority: 'medium',
    team: 'Facilities',
    status: 'Awaiting confirmation',
    statusKind: 'awaiting',
    flags: ['overdue'],
    age: '5h 20m',
  },
  {
    ticket: 'CC-1031',
    issue: 'Wi-Fi dropping repeatedly',
    location: 'Hostel Block C',
    priority: 'low',
    team: 'Network Ops',
    status: 'Awaiting confirmation',
    statusKind: 'awaiting',
    flags: ['repeated'],
    age: '1d',
  },
  {
    ticket: 'CC-1029',
    issue: 'Broken chair batch',
    location: 'Seminar Room 4',
    priority: 'low',
    team: 'Facilities',
    status: 'Assigned',
    statusKind: 'assigned',
    flags: [],
    age: '6h',
  },
]

export type ActivityItem = {
  id: string
  kind: 'done' | 'active' | 'warn'
  text: string
  meta: string
  time: string
}

export const agentActivity: ActivityItem[] = [
  { id: 'a1', kind: 'done', text: 'Ticket CC-1048 created', meta: 'Computer Lab 3', time: 'now' },
  { id: 'a2', kind: 'done', text: 'Incident history retrieved', meta: '3 records · PC-03-17', time: '12s' },
  { id: 'a3', kind: 'done', text: 'IT Support notified', meta: 'SMS + email', time: '20s' },
  { id: 'a4', kind: 'active', text: 'Follow-up scheduled', meta: 'CC-1048 · 30 min', time: '25s' },
  { id: 'a5', kind: 'warn', text: 'Escalation required', meta: 'CC-1044 overdue 40m', time: '1m' },
  { id: 'a6', kind: 'done', text: 'Resolution verified', meta: 'CC-1039 · reporter confirmed', time: '4m' },
  { id: 'a7', kind: 'done', text: 'Repeated issue prioritized', meta: 'CC-1031 · Wi-Fi', time: '8m' },
]

/* Campus buildings — stylized grid coordinates (percentages), NOT geographic */
export type Building = {
  id: string
  name: string
  short: string
  x: number
  y: number
  w: number
  h: number
  active: number
  resolved: number
  topPriority: Priority
}

export const buildings: Building[] = [
  { id: 'eng', name: 'Engineering Block', short: 'ENG', x: 6, y: 10, w: 26, h: 30, active: 5, resolved: 8, topPriority: 'high' },
  { id: 'sci', name: 'Science Block', short: 'SCI', x: 38, y: 8, w: 24, h: 24, active: 4, resolved: 5, topPriority: 'high' },
  { id: 'lib', name: 'Library', short: 'LIB', x: 68, y: 12, w: 26, h: 26, active: 2, resolved: 11, topPriority: 'medium' },
  { id: 'adm', name: 'Admin Block', short: 'ADM', x: 8, y: 48, w: 22, h: 22, active: 3, resolved: 4, topPriority: 'high' },
  { id: 'lec', name: 'Lecture Halls', short: 'LEC', x: 36, y: 40, w: 28, h: 20, active: 3, resolved: 6, topPriority: 'medium' },
  { id: 'hos', name: 'Hostel Block C', short: 'HOS', x: 70, y: 46, w: 24, h: 24, active: 2, resolved: 3, topPriority: 'low' },
  { id: 'sem', name: 'Seminar Wing', short: 'SEM', x: 10, y: 76, w: 24, h: 18, active: 1, resolved: 2, topPriority: 'low' },
  { id: 'spo', name: 'Sports Complex', short: 'SPO', x: 40, y: 68, w: 24, h: 26, active: 0, resolved: 4, topPriority: 'resolved' },
  { id: 'caf', name: 'Cafeteria', short: 'CAF', x: 70, y: 76, w: 22, h: 18, active: 1, resolved: 5, topPriority: 'low' },
]

export const distribution = [
  { category: 'IT / Computers', count: 9, tone: 'high' as const },
  { category: 'Electrical', count: 6, tone: 'high' as const },
  { category: 'HVAC / AC', count: 5, tone: 'medium' as const },
  { category: 'Network', count: 4, tone: 'medium' as const },
  { category: 'Furniture', count: 3, tone: 'low' as const },
  { category: 'Plumbing', count: 1, tone: 'low' as const },
]

export const priorityBreakdown = [
  { name: 'High', value: 6, key: 'high' as Priority },
  { name: 'Medium', value: 9, key: 'medium' as Priority },
  { name: 'Low', value: 13, key: 'low' as Priority },
  { name: 'Resolved', value: 19, key: 'resolved' as Priority },
]
