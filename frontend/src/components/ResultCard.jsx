import './ResultCard.css'

const VERDICT_META = {
  likely_qualifies:    { label: 'Likely Qualifies',   color: 'pass',  icon: '✅' },
  possibly_qualifies:  { label: 'Possibly Qualifies',  color: 'warn',  icon: '⚡' },
  unlikely_to_qualify: { label: 'Unlikely to Qualify', color: 'fail',  icon: '✗'  },
}

export default function ResultCard({ scheme, lang }) {
  const meta = VERDICT_META[scheme.verdict] || VERDICT_META.unlikely_to_qualify
  const confidence = scheme.confidence_score ?? 0
  const confidenceLevel = scheme.confidence_level ?? ''

  return (
    <div className={`result-card result-card--${meta.color}`}>
      <div className="rc-header">
        <div className="rc-title-group">
          <span className="rc-icon">{meta.icon}</span>
          <div>
            <h3 className="rc-name">{scheme.scheme_name}</h3>
            {scheme.scheme_id && (
              <span className="rc-id">{scheme.scheme_id.toUpperCase()}</span>
            )}
          </div>
        </div>
        <div className="rc-confidence">
          <div className={`confidence-badge confidence--${confidenceLevel?.toLowerCase()}`}>
            {confidenceLevel}
          </div>
          <div className="confidence-score">{confidence}%</div>
        </div>
      </div>

      <div className="confidence-bar-wrap">
        <div
          className={`confidence-bar-fill confidence-bar--${meta.color}`}
          style={{ width: `${confidence}%` }}
        />
      </div>

      {scheme.next_step && (
        <div className="rc-next-step">
          <span className="next-step-label">
            {lang === 'hi' ? 'अगला कदम' : 'Next step'}
          </span>
          <p>{scheme.next_step}</p>
        </div>
      )}

      {scheme.missing_fields?.length > 0 && (
        <div className="rc-missing">
          <span className="missing-label">
            ⚠️ {lang === 'hi' ? 'जानकारी चाहिए' : 'Info needed'}:
          </span>
          {scheme.missing_fields.map((f, i) => (
            <span key={i} className="missing-tag">{f}</span>
          ))}
        </div>
      )}
    </div>
  )
}
