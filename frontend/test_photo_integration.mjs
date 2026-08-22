/**
 * test_photo_integration.mjs
 *
 * Comprehensive Test Suite for Photo Upload & Multi-Modal Gemini Vision Integration:
 * 1. Test 1: Upload a projector image with text "This is the projector in Lab 3."
 *    -> backend Gemini Vision analysis -> combined goal -> existing /agent/run workflow -> execution & outcome
 * 2. Test 2: Voice workflow without photo -> verify text-only transcription execution
 * 3. Test 3: Text-only locked demo scenario -> verify original workflow
 * 4. Test 4: Combined Photo + detailed text scenario -> verify synthesized combined goal contains both context
 * 5. Verify Frontend UI contains Photo button with file input / camera capture
 */

const FRONTEND_URL = 'http://localhost:3000'
const BACKEND_URL = 'http://127.0.0.1:8000'

const TINY_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

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

async function analyzeImageViaBackend(pngBuffer, userText) {
  const boundary = '----WebKitFormBoundary' + Math.random().toString(36).substring(2)
  let bodyParts = []

  // Add file field
  bodyParts.push(
    `--${boundary}\r\n` +
    `Content-Disposition: form-data; name="file"; filename="lab3_projector.png"\r\n` +
    `Content-Type: image/png\r\n\r\n`
  )
  const headerBuf = Buffer.from(bodyParts.join(''), 'utf-8')

  // Text field
  let textField = ''
  if (userText) {
    textField =
      `\r\n--${boundary}\r\n` +
      `Content-Disposition: form-data; name="user_text"\r\n\r\n` +
      `${userText}\r\n--${boundary}--\r\n`
  } else {
    textField = `\r\n--${boundary}--\r\n`
  }
  const footerBuf = Buffer.from(textField, 'utf-8')

  const fullBody = Buffer.concat([headerBuf, pngBuffer, footerBuf])

  const res = await fetch(`${BACKEND_URL}/agent/analyze-image`, {
    method: 'POST',
    headers: {
      'Content-Type': `multipart/form-data; boundary=${boundary}`,
    },
    body: fullBody,
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`POST /agent/analyze-image failed (HTTP ${res.status}): ${errText}`)
  }

  return res.json()
}

async function main() {
  console.log(SEP)
  console.log('PHOTO UPLOAD & GEMINI VISION ANALYSIS INTEGRATION SUITE')
  console.log(SEP)

  const pngBuffer = Buffer.from(TINY_PNG_BASE64, 'base64')

  // -------------------------------------------------------------------------
  // FRONTEND UI VERIFICATION
  // -------------------------------------------------------------------------
  console.log('\n[0] Checking Frontend DOM for Photo Upload Elements...')
  const feRes = await fetch(FRONTEND_URL)
  check('Frontend is responding with HTTP 200', feRes.status === 200)
  const feHtml = await feRes.text()
  check('Contains Photo button', feHtml.includes('Photo') || feHtml.includes('photo'))
  check('Contains hidden image file input', feHtml.includes('type="file"') || feHtml.includes('accept="image/jpeg,image/png,image/webp"'))

  // -------------------------------------------------------------------------
  // TEST 1: Photo Upload + Text Context (Lab 3 Projector)
  // -------------------------------------------------------------------------
  console.log('\n[TEST 1] Photo Upload with Context: "This is the projector in Lab 3."')
  const userText1 = 'This is the projector in Lab 3.'
  const visionRes1 = await analyzeImageViaBackend(pngBuffer, userText1)

  check('POST /agent/analyze-image returned 200', visionRes1 !== null)
  check('Returned structured analysis object', typeof visionRes1.analysis === 'object')
  check('Identified equipment / issue', Boolean(visionRes1.analysis.issue || visionRes1.analysis.equipment))
  check('Generated combined goal containing user context', visionRes1.combined_goal.includes('Lab 3'))
  console.log(`  Synthesized Combined Goal: "${visionRes1.combined_goal}"`)

  // Execute synthesized goal via existing agent workflow
  const exec1 = await runGoalAndPoll(visionRes1.combined_goal, 1)
  check('Agent workflow executed to COMPLETED', exec1.taskData.status === 'COMPLETED')
  check('Maintenance ticket generated / verified', typeof exec1.taskData.outcome?.ticket_id === 'number')
  check('Technician notified', exec1.taskData.outcome?.technician_notified === true)

  // -------------------------------------------------------------------------
  // TEST 2: Voice Workflow without Photo
  // -------------------------------------------------------------------------
  console.log('\n[TEST 2] Voice Workflow (Without Photo)')
  const voiceTranscribed = "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."
  const exec2 = await runGoalAndPoll(voiceTranscribed, 1)
  check('Voice goal executed to COMPLETED', exec2.taskData.status === 'COMPLETED')
  check('Priority is HIGH', exec2.taskData.outcome?.priority === 'HIGH')
  check('Reporter is Arjun Reddy', exec2.taskData.outcome?.reporter?.name === 'Arjun Reddy')

  // -------------------------------------------------------------------------
  // TEST 3: Original Text-Only Workflow
  // -------------------------------------------------------------------------
  console.log('\n[TEST 3] Original Text-Only Workflow')
  const textGoal = "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."
  const exec3 = await runGoalAndPoll(textGoal, 1)
  check('Text-only goal executed to COMPLETED', exec3.taskData.status === 'COMPLETED')
  check('Ticket #1 verified', exec3.taskData.outcome?.ticket_id === 1)

  // -------------------------------------------------------------------------
  // TEST 4: Photo + Urgent Student Context Combined
  // -------------------------------------------------------------------------
  console.log('\n[TEST 4] Photo + Urgent Student Speech/Text Combined')
  const urgentText = 'Projector in Lab 3 is completely dark and broken. Project presentation tomorrow morning at 10 AM.'
  const visionRes4 = await analyzeImageViaBackend(pngBuffer, urgentText)

  check('Combined goal preserves urgency & location',
    visionRes4.combined_goal.includes('Lab 3') && visionRes4.combined_goal.includes('10 AM'))
  console.log(`  Combined Multi-Modal Goal: "${visionRes4.combined_goal}"`)

  const exec4 = await runGoalAndPoll(visionRes4.combined_goal, 1)
  check('Multi-modal task reached COMPLETED', exec4.taskData.status === 'COMPLETED')
  check('Determined HIGH priority from urgent timeline & history', exec4.taskData.outcome?.priority === 'HIGH')

  console.log('\n' + SEP)
  if (allOk) {
    console.log('ALL PHOTO & VISION INTEGRATION TESTS PASSED')
  } else {
    console.log('ONE OR MORE TESTS FAILED')
    process.exit(1)
  }
}

main().catch((err) => {
  console.error('Test Execution Error:', err)
  process.exit(1)
})
