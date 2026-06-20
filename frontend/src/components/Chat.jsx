import { useState, useRef, useEffect } from 'react'
import Message from './Message.jsx'
import './Chat.css'

const HERO_QUESTIONS = [
  { field: 'age',                      label: 'Age',               hint: 'e.g. 42' },
  { field: 'gender',                   label: 'Gender',            hint: 'Male / Female / Other' },
  { field: 'caste_category',           label: 'Caste category',    hint: 'SC / ST / OBC / General' },
  { field: 'state',                    label: 'State',             hint: 'e.g. Uttar Pradesh' },
  { field: 'location_type',            label: 'Rural or Urban?',   hint: 'rural / urban' },
  { field: 'monthly_household_income', label: 'Monthly income (₹)', hint: 'e.g. 8000' },
  { field: 'employment_type',          label: 'Employment type',   hint: 'farmer / daily_wage / salaried / unemployed' },
  { field: 'housing_type',             label: 'Housing type',      hint: 'pucca / kutcha / homeless' },
  { field: 'land_holding_acres',       label: 'Land owned (acres)', hint: '0 if none' },
]

function inferCurrentField(col) {
  for (const q of HERO_QUESTIONS) {
    const v = col[q.field]
    if (v === undefined || v === null || v === '') return q
  }
  return null
}

export default function Chat({ onResults, lang }) {
  const [messages, setMessages]       = useState([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [started, setStarted]         = useState(false)
  const [currentField, setCurrentField] = useState(null)
  const [progress, setProgress]       = useState(0)

  // Use a ref so async callbacks always see the latest collected — no stale closure
  const collectedRef = useRef({})
  const bottomRef    = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function pushMsg(role, text) {
    setMessages(prev => [...prev, { role, text, id: Date.now() + Math.random() }])
  }

  function updateCollected(newCol) {
    collectedRef.current = newCol
    const filled = HERO_QUESTIONS.filter(q => newCol[q.field] !== undefined && newCol[q.field] !== '').length
    setProgress(Math.round((filled / HERO_QUESTIONS.length) * 100))
    setCurrentField(inferCurrentField(newCol))
  }

  async function startChat() {
    setStarted(true)
    pushMsg('bot', lang === 'hi'
      ? 'नमस्ते! मैं आपकी सरकारी योजनाओं के लिए पात्रता जांचने में मदद करूंगा।'
      : "Hello! I'm YojanaPath. I'll check which government schemes you qualify for. Answer a few quick questions."
    )
    await askNext({}, '')
  }

  async function askNext(col, userMessage) {
    setLoading(true)
    try {
      const res  = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collected: col, message: userMessage }),
      })
      const data = await res.json()
      setLoading(false)

      // Server echoes back collected (may add 'language') — use it as truth
      const serverCol = data.collected && Object.keys(data.collected).length > 0
        ? data.collected
        : col
      updateCollected(serverCol)

      if (data.next_question) {
        pushMsg('bot', data.next_question)
      } else if (data.action === 'analyze') {
        pushMsg('bot', lang === 'hi'
          ? '✅ सभी जानकारी मिल गई। अब योजनाओं की जांच हो रही है...'
          : '✅ Got all the info! Analyzing your eligibility now...'
        )
        await runAnalysis(serverCol)
      }
    } catch {
      setLoading(false)
      pushMsg('bot', 'Something went wrong — is the backend running?')
    }
  }

  async function runAnalysis(userData) {
    setLoading(true)
    try {
      const res  = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_data: { ...userData, language: lang } }),
      })
      const data = await res.json()
      setLoading(false)
      onResults(data)
    } catch {
      setLoading(false)
      pushMsg('bot', 'Analysis failed. Check your GROQ_API_KEY in backend/.env')
    }
  }

  async function handleSend() {
    const val = input.trim()
    if (!val || loading) return
    pushMsg('user', val)
    setInput('')

    // Read latest collected from ref (never stale, unlike useState)
    const latest = collectedRef.current
    const field  = inferCurrentField(latest)          // which field to fill now
    const next   = { ...latest }
    if (field) next[field.field] = val
    updateCollected(next)                             // update ref + UI immediately

    await askNext(next, val)
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const filled = HERO_QUESTIONS.filter(q => {
    const v = collectedRef.current[q.field]
    return v !== undefined && v !== ''
  }).length

  return (
    <div className="chat-outer">
      {!started ? (
        <div className="chat-hero">
          <div className="hero-badge">USAII Global AI Hackathon 2026 · Brief 4</div>
          <h1 className="hero-title">
            {lang === 'hi' ? 'आपके लिए कौन सी सरकारी योजनाएं हैं?' : 'Which government schemes are you eligible for?'}
          </h1>
          <p className="hero-sub">
            {lang === 'hi'
              ? '6 सवालों में जानें — हिंदी या अंग्रेजी में। कोई डेटा सेव नहीं होता।'
              : '9 quick questions. Full reasoning. In your language. No data stored.'}
          </p>
          <div className="hero-persona">
            <div className="persona-icon">👨‍🌾</div>
            <div className="persona-text">
              <strong>Ramesh, 42, UP</strong>
              <span>"I lost a full day's wages visiting the block office — turned away for a missing document."</span>
            </div>
          </div>
          <div className="scheme-pills">
            {['PM-KISAN','PMJAY','PMAY-G','MGNREGA','PDS','NSP'].map(s => (
              <span key={s} className="scheme-pill">{s}</span>
            ))}
          </div>
          <button className="start-btn" onClick={startChat}>
            {lang === 'hi' ? '🚀 शुरू करें' : '🚀 Check My Eligibility'}
          </button>
        </div>
      ) : (
        <div className="chat-container">
          <div className="progress-bar-wrap">
            <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-label">
            {progress}% complete · {filled}/{HERO_QUESTIONS.length} questions
          </div>

          <div className="messages">
            {messages.map(m => <Message key={m.id} msg={m} />)}
            {loading && (
              <div className="message bot">
                <div className="msg-bubble bot-bubble typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="chat-input-row">
            {currentField && (
              <div className="field-hint">
                <span className="hint-label">{currentField.label}</span>
                <span className="hint-val">{currentField.hint}</span>
              </div>
            )}
            <div className="input-wrap">
              <input
                className="chat-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder={lang === 'hi' ? 'अपना जवाब लिखें...' : 'Type your answer...'}
                disabled={loading}
                autoFocus
              />
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={loading || !input.trim()}
              >
                {loading ? <span className="spinner" /> : '➤'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
