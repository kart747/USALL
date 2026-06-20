import { useState } from 'react'
import './ReasoningChain.css'

export default function ReasoningChain({ chain, lang }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="reasoning-wrap">
      <button className="reasoning-toggle" onClick={() => setOpen(o => !o)}>
        <span>🔍 {lang === 'hi' ? 'कारण देखें' : 'View Reasoning'}</span>
        <span className="toggle-arrow">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="reasoning-body">
          <p className="reasoning-intro">
            {lang === 'hi'
              ? 'नीचे दिखाया गया है कि आपकी जानकारी नियमों से कैसे मेल खाती है:'
              : 'Here is how your situation maps to the scheme rules:'}
          </p>
          <div className="reasoning-table-wrap">
            <table className="reasoning-table">
              <thead>
                <tr>
                  <th>{lang === 'hi' ? 'आपकी स्थिति' : 'Your Situation'}</th>
                  <th>{lang === 'hi' ? 'नियम' : 'Rule'}</th>
                  <th>{lang === 'hi' ? 'परिणाम' : 'Result'}</th>
                </tr>
              </thead>
              <tbody>
                {chain.map((row, i) => (
                  <tr key={i} className={`reasoning-row row--${row.result}`}>
                    <td className="col-user">{row.user_value}</td>
                    <td className="col-rule">{row.rule}</td>
                    <td className="col-result">
                      <span className={`result-chip chip--${row.result}`}>
                        {row.result === 'pass' ? '✓' : row.result === 'fail' ? '✗' : '?'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {chain[0]?.explanation && (
            <p className="reasoning-explanation">{chain[0].explanation}</p>
          )}
        </div>
      )}
    </div>
  )
}
