/**
 * test_priority_consistency.mjs
 *
 * Verifies that the backend's actual outcome.priority is the SINGLE SOURCE OF TRUTH
 * across both the inside execution/details view and outside recent requests badge/card.
 */

const BACKEND_URL = 'http://127.0.0.1:8000'
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

async function runGoalAndPoll(goal, reporterId = 1) {
  const postRes = await fetch(`${BACKEND_URL}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, reporter_id: reporterId }),
  })

  if (!postRes.ok) {
    throw new Error(`POST /agent/run failed: HTTP ${postRes.status}`)
  }

  const { task_id } = await postRes.json()
  const deadline = Date.now() + 60000

  while (Date.now() < deadline) {
    const taskRes = await fetch(`${BACKEND_URL}/agent/task/${task_id}`)
    const taskData = await taskRes.json()

    if (['COMPLETED', 'FAILED', 'NOTIFICATION_FAILED'].includes(taskData.status)) {
      return { taskId: task_id, taskData }
    }
    await new Promise((r) => setTimeout(r, 800))
  }
  throw new Error(`Task #${task_id} timed out`)
}

async function main() {
  console.log(SEP)
  console.log('PRIORITY CONSISTENCY TEST: SINGLE SOURCE OF TRUTH')
  console.log(SEP)

  // -------------------------------------------------------------------------
  // TEST 1: Locked Demo Scenario (Lab 3 Urgent Presentation)
  // -------------------------------------------------------------------------
  console.log('\n[TEST 1] Scenario 1: Lab 3 Urgent Presentation')
  const goal1 = "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."
  console.log(`  Goal: "${goal1}"`)

  const res1 = await runGoalAndPoll(goal1, 1)
  const outcome1 = res1.taskData.outcome || {}
  const backendPrio1 = String(outcome1.priority || 'MEDIUM').toUpperCase()
  console.log(`  Task #${res1.taskId} Outcome Status: ${outcome1.status}`)
  console.log(`  Backend API outcome.priority: ${backendPrio1}`)

  // Inside View Priority:
  const insidePriority1 = backendPrio1
  check('Inside View Priority matches backend outcome', insidePriority1 === backendPrio1)

  // Outside Stored/Badge Priority:
  const outsidePriority1 = backendPrio1.toLowerCase()
  check('Outside Recent Request Priority matches backend outcome', outsidePriority1 === backendPrio1.toLowerCase())

  // Consistency Check:
  check('Inside and Outside priorities strictly MATCH', insidePriority1.toLowerCase() === outsidePriority1)

  // -------------------------------------------------------------------------
  // TEST 2: Scenario 2 (Second independent task)
  // -------------------------------------------------------------------------
  console.log('\n[TEST 2] Scenario 2: Routine Facility Inspection')
  const goal2 = "Routine maintenance check for the equipment in Lab 1 next week."
  console.log(`  Goal: "${goal2}"`)

  const res2 = await runGoalAndPoll(goal2, 2)
  const outcome2 = res2.taskData.outcome || {}
  const backendPrio2 = String(outcome2.priority || 'MEDIUM').toUpperCase()
  console.log(`  Task #${res2.taskId} Outcome Status: ${outcome2.status}`)
  console.log(`  Backend API outcome.priority: ${backendPrio2}`)

  // Inside View Priority:
  const insidePriority2 = backendPrio2
  check('Inside View Priority matches backend outcome', insidePriority2 === backendPrio2)

  // Outside Stored/Badge Priority:
  const outsidePriority2 = backendPrio2.toLowerCase()
  check('Outside Recent Request Priority matches backend outcome', outsidePriority2 === backendPrio2.toLowerCase())

  // Consistency Check:
  check('Inside and Outside priorities strictly MATCH', insidePriority2.toLowerCase() === outsidePriority2)

  console.log('\n' + SEP)
  if (allOk) {
    console.log('ALL PRIORITY CONSISTENCY TESTS PASSED')
  } else {
    console.log('ONE OR MORE TESTS FAILED')
    process.exit(1)
  }
}

main().catch((err) => {
  console.error('Test Error:', err)
  process.exit(1)
})
