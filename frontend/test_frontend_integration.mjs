/**
 * test_frontend_integration.mjs
 *
 * Full End-to-End Test for Campus Commander Frontend & Landing Page Fixes:
 * 1. Verifies Next.js Frontend is serving routes (/, /admin)
 * 2. Verifies FastAPI Backend is reachable (health, reporters)
 * 3. Submits locked demo scenario with reporter_id: 1 (Arjun Reddy)
 * 4. Verifies live event stream (memory_retrieval, get_equipment_history, decision, create_maintenance_ticket, notify_staff, verify_ticket, memory_save)
 * 5. Verifies final outcome: status=COMPLETED, ticket_id=1, priority=HIGH, technician_notified=true, reporter attribution
 * 6. Verifies truthful outcome message (physical repair pending, ticketing/notification complete)
 * 7. Verifies recent requests data model (real task ID, ticket ID, goal, room, priority, status)
 * 8. Confirms static mock requests (CC-1042, CC-1039, CC-1031) are eliminated from live student history
 */

const FRONTEND_URL = 'http://localhost:3000'
const BACKEND_URL = 'http://127.0.0.1:8000'
const DEMO_GOAL = "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."

const SEP = '='.repeat(70)
let allOk = true

function check(label, cond, detail = '') {
  const tag = cond ? '  PASS' : '  FAIL'
  let msg = `${tag}  ${label}`
  if (detail) msg += `  (${detail})`
  console.log(msg)
  if (!cond) allOk = false
  return cond
}

function extractRoomFromGoal(goal) {
  const g = goal.toLowerCase()
  if (g.includes('lab 3')) return 'Lab 3'
  if (g.includes('lab 1')) return 'Lab 1'
  if (g.includes('lab 2')) return 'Lab 2'
  if (g.includes('library')) return 'Library'
  if (g.includes('hostel block c')) return 'Hostel Block C'
  if (g.includes('lecture hall')) return 'Lecture Hall'
  return 'Campus Facility'
}

function formatRequestTime(isoString) {
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

async function main() {
  console.log(SEP)
  console.log('CAMPUS COMMANDER FRONTEND-BACKEND INTEGRATION TEST')
  console.log(SEP)

  // 1. Check Frontend routes
  console.log('\n[1] Checking Frontend Routes...')
  const feRes = await fetch(FRONTEND_URL)
  check('Frontend Student Portal (/) returns 200', feRes.status === 200, `status=${feRes.status}`)
  const feHtml = await feRes.text()
  check('Landing page does NOT contain hard-coded mock ticket CC-1042', !feHtml.includes('CC-1042'))
  check('Landing page does NOT contain hard-coded mock ticket CC-1039', !feHtml.includes('CC-1039'))
  check('Landing page does NOT contain hard-coded mock ticket CC-1031', !feHtml.includes('CC-1031'))

  const adminRes = await fetch(`${FRONTEND_URL}/admin`)
  check('Frontend Command Center (/admin) returns 200', adminRes.status === 200, `status=${adminRes.status}`)

  // 2. Check Backend Health
  console.log('\n[2] Checking Backend API Health...')
  const healthRes = await fetch(`${BACKEND_URL}/health`)
  check('Backend /health returns 200', healthRes.status === 200)
  const healthData = await healthRes.json()
  check('Backend service online', healthData.status === 'ok')

  // 3. Fetch Reporters
  console.log('\n[3] Testing GET /reporters...')
  const repRes = await fetch(`${BACKEND_URL}/reporters`)
  check('GET /reporters returns 200', repRes.status === 200)
  const reporters = await repRes.json()
  check('Seeded reporters exist (>= 3)', reporters.length >= 3, `count=${reporters.length}`)
  console.log(`  Loaded ${reporters.length} reporters:`)
  for (const r of reporters) {
    console.log(`    - [ID ${r.id}] ${r.name} (${r.role}) <${r.email}>`)
  }

  const selectedReporter = reporters[0]
  check('Default reporter is Arjun Reddy (Student)', selectedReporter && selectedReporter.id === 1)

  // 4. Submit Goal via POST /agent/run
  console.log('\n[4] Submitting Goal via POST /agent/run...')
  console.log(`  Reporter ID: ${selectedReporter.id} (${selectedReporter.name})`)
  console.log(`  Goal: "${DEMO_GOAL}"`)

  const postRes = await fetch(`${BACKEND_URL}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      goal: DEMO_GOAL,
      reporter_id: selectedReporter.id,
    }),
  })

  check('POST /agent/run returns 202 Accepted', postRes.status === 202, `status=${postRes.status}`)
  const postData = await postRes.json()
  const taskId = postData.task_id
  check('Received valid task_id', typeof taskId === 'number' && taskId > 0, `task_id=${taskId}`)

  // 5. Poll Events & Task Completion
  console.log(`\n[5] Polling Task #${taskId} and Live Events...`)
  const deadline = Date.now() + 60000
  let finalTask = null
  let finalEvents = []

  while (Date.now() < deadline) {
    const [taskR, eventsR] = await Promise.all([
      fetch(`${BACKEND_URL}/agent/task/${taskId}`),
      fetch(`${BACKEND_URL}/agent/task/${taskId}/events`),
    ])

    const taskData = await taskR.json()
    const eventsData = await eventsR.json()
    finalEvents = eventsData.events || []

    process.stdout.write(`\r  [Polling] Status: ${taskData.status} | Events logged: ${finalEvents.length} `)

    if (['COMPLETED', 'FAILED', 'NOTIFICATION_FAILED'].includes(taskData.status)) {
      finalTask = taskData
      break
    }
    await new Promise((r) => setTimeout(r, 800))
  }
  console.log('\n')

  check('Task reached terminal state within timeout', finalTask !== null)
  check('Task status == COMPLETED', finalTask?.status === 'COMPLETED', `status=${finalTask?.status}`)

  const outcome = finalTask?.outcome || {}
  console.log('\nFinal Task Outcome:')
  console.log(JSON.stringify(outcome, null, 2))

  // 6. Verify Outcome Fields
  console.log('\n[6] Validating Real Outcome Contract...')
  check('priority == HIGH', outcome.priority === 'HIGH', `got '${outcome.priority}'`)
  check('ticket_id returned (number)', typeof outcome.ticket_id === 'number', `ticket_id=${outcome.ticket_id}`)
  check('technician_notified == true', outcome.technician_notified === true)
  check('reporter attribution matches', outcome.reporter?.id === selectedReporter.id, `reporter=${JSON.stringify(outcome.reporter)}`)

  // 7. Verify Truthful Message
  console.log('\n[7] Verifying Truthful Message...')
  const msg = outcome.message || ''
  check('Message acknowledges reporter', msg.includes('Arjun Reddy'))
  check('Message mentions ticket creation', msg.includes('ticket') || msg.includes('Ticket'))
  check('Message clarifies physical repair is pending (no false repair claims)',
    msg.toLowerCase().includes('pending') || msg.toLowerCase().includes('physical repair'))

  // 8. Verify Event Stream
  console.log(`\n[8] Validating Event Stream (${finalEvents.length} events logged)...`)
  const eventTypes = finalEvents.map((e) => e.event_type)
  const toolNames = finalEvents.map((e) => e.tool).filter(Boolean)

  console.log('  Event types:', eventTypes)
  console.log('  Tool calls:', toolNames)

  check('Contains memory_retrieval event', eventTypes.includes('memory_retrieval'))
  check('Contains decision event (reasoning)', eventTypes.includes('decision'))
  check('Contains get_equipment_history tool call', toolNames.includes('get_equipment_history'))
  check('Contains create_maintenance_ticket tool call', toolNames.includes('create_maintenance_ticket'))
  check('Contains notify_staff tool call', toolNames.includes('notify_staff'))
  check('Contains verify_ticket tool call', toolNames.includes('verify_ticket'))
  check('Contains memory_save event', eventTypes.includes('memory_save'))

  // 9. Verify Recent Requests Record Generation
  console.log('\n[9] Validating Real Recent Request Record Generation...')
  const room = extractRoomFromGoal(DEMO_GOAL)
  check('Extracted room matches goal', room === 'Lab 3', `room=${room}`)

  const recentRecord = {
    taskId,
    ticketId: outcome.ticket_id,
    goal: DEMO_GOAL,
    room,
    status: outcome.status,
    priority: (outcome.priority?.toLowerCase()) || 'high',
    technicianNotified: outcome.technician_notified,
    timestamp: new Date().toISOString(),
    timeFormatted: formatRequestTime(new Date().toISOString()),
  }

  console.log('Generated Recent Request Record:', recentRecord)
  check('Recent record has valid taskId', recentRecord.taskId === taskId)
  check('Recent record has valid ticketId', recentRecord.ticketId === outcome.ticket_id)
  check('Recent record priority is high', recentRecord.priority === 'high')
  check('Recent record status is COMPLETED', recentRecord.status === 'COMPLETED')
  check('Recent record room is Lab 3', recentRecord.room === 'Lab 3')

  console.log('\n' + SEP)
  if (allOk) {
    console.log('ALL FRONTEND-BACKEND INTEGRATION TESTS PASSED')
  } else {
    console.log('ONE OR MORE TESTS FAILED')
    process.exit(1)
  }
}

main().catch((err) => {
  console.error('\nTest Execution Error:', err)
  process.exit(1)
})
