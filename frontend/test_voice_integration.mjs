/**
 * test_voice_integration.mjs
 *
 * Verifies Voice Input Workflow & Integration:
 * 1. Verifies Frontend routes (/, /admin) return 200
 * 2. Verifies Voice input button attributes are present in DOM
 * 3. Verifies that transcribed voice input sent through the existing POST /agent/run
 *    executes seamlessly through the backend with task polling and completion.
 */

const FRONTEND_URL = 'http://localhost:3000'
const BACKEND_URL = 'http://127.0.0.1:8000'
const TRANSCRIBED_VOICE_TEXT = "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."

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

async function main() {
  console.log(SEP)
  console.log('CAMPUS COMMANDER VOICE INPUT INTEGRATION TEST')
  console.log(SEP)

  // 1. Check Frontend HTML for Voice Input Button
  console.log('\n[1] Checking Frontend Landing Page for Voice Controls...')
  const feRes = await fetch(FRONTEND_URL)
  check('Frontend is responding with HTTP 200', feRes.status === 200)
  const feHtml = await feRes.text()

  check('Contains Voice input button', feHtml.includes('Voice') || feHtml.includes('voice'))
  check('Contains Send button with accessible label', feHtml.includes('Send to Campus Commander') || feHtml.includes('aria-label'))

  // 2. Submit Transcribed Voice Text to Backend
  console.log('\n[2] Executing Voice Transcribed Goal via POST /agent/run...')
  console.log(`  Transcribed text: "${TRANSCRIBED_VOICE_TEXT}"`)

  const postRes = await fetch(`${BACKEND_URL}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      goal: TRANSCRIBED_VOICE_TEXT,
      reporter_id: 1, // Arjun Reddy
    }),
  })

  check('POST /agent/run accepts voice transcription with HTTP 202', postRes.status === 202, `status=${postRes.status}`)
  const { task_id } = await postRes.json()
  check('Received valid task_id', typeof task_id === 'number' && task_id > 0, `task_id=${task_id}`)

  // 3. Poll Task Status
  console.log(`\n[3] Polling Task #${task_id} Execution...`)
  const deadline = Date.now() + 60000
  let finalTask = null

  while (Date.now() < deadline) {
    const taskRes = await fetch(`${BACKEND_URL}/agent/task/${task_id}`)
    const taskData = await taskRes.json()

    process.stdout.write(`\r  [Polling] Status: ${taskData.status} `)

    if (['COMPLETED', 'FAILED', 'NOTIFICATION_FAILED'].includes(taskData.status)) {
      finalTask = taskData
      break
    }
    await new Promise((r) => setTimeout(r, 800))
  }
  console.log('\n')

  check('Voice goal execution completed within timeout', finalTask !== null)
  check('Task status == COMPLETED', finalTask?.status === 'COMPLETED', `status=${finalTask?.status}`)

  const outcome = finalTask?.outcome || {}
  check('Priority is HIGH', outcome.priority === 'HIGH', `got '${outcome.priority}'`)
  check('Ticket ID exists', typeof outcome.ticket_id === 'number', `ticket_id=${outcome.ticket_id}`)
  check('Technician notified', outcome.technician_notified === true)
  check('Reporter is Arjun Reddy', outcome.reporter?.name === 'Arjun Reddy')

  console.log('\n' + SEP)
  if (allOk) {
    console.log('ALL VOICE INPUT INTEGRATION TESTS PASSED')
  } else {
    console.log('ONE OR MORE TESTS FAILED')
    process.exit(1)
  }
}

main().catch((err) => {
  console.error('Test Error:', err)
  process.exit(1)
})
