import { useState } from 'react'
import './HandoffCard.css'

export default function HandoffCard({ handoff, lang }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(handoff.handoff_summary || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="handoff-card">
      <div className="handoff-header">
        <div className="handoff-icon">🏢</div>
        <div>
          <h3 className="handoff-title">
            {lang === 'hi' ? 'VLE ऑपरेटर को दिखाएं' : 'Show this to the VLE Operator'}
          </h3>
          <p className="handoff-sub">
            {lang === 'hi'
              ? 'अपने नजदीकी CSC पर यह संदेश दिखाएं'
              : 'Take this summary to your nearest Common Service Centre'}
          </p>
        </div>
      </div>

      {handoff.schemes_to_apply?.length > 0 && (
        <div className="handoff-schemes">
          {handoff.schemes_to_apply.map((s, i) => (
            <span key={i} className="handoff-scheme-tag">{s}</span>
          ))}
        </div>
      )}

      {handoff.handoff_summary && (
        <div className="handoff-summary">
          <p>{handoff.handoff_summary}</p>
          <button className="copy-btn" onClick={copy}>
            {copied ? '✓ Copied!' : '📋 Copy'}
          </button>
        </div>
      )}

      {handoff.csc_instruction && (
        <div className="handoff-instruction">
          <span className="instr-label">
            {lang === 'hi' ? 'VLE के लिए निर्देश' : 'Instruction for VLE'}:
          </span>
          <p>{handoff.csc_instruction}</p>
        </div>
      )}

      <div className="handoff-cta">
        <span>📍</span>
        <a
          href="https://locator.csccloud.in/"
          target="_blank"
          rel="noopener noreferrer"
        >
          {lang === 'hi' ? 'नजदीकी CSC खोजें →' : 'Find nearest CSC →'}
        </a>
      </div>
    </div>
  )
}
