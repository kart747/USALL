import ResultCard from './ResultCard.jsx'
import ReasoningChain from './ReasoningChain.jsx'
import DocumentChecklist from './DocumentChecklist.jsx'
import HandoffCard from './HandoffCard.jsx'
import SummaryBanner from './SummaryBanner.jsx'
import './ResultsPage.css'

export default function ResultsPage({ data, lang }) {
  const schemes = data?.eligibility?.schemes || []
  const documents = data?.documents?.documents || []
  const handoff = data?.handoff || {}
  const stackingSummary = data?.stacking_summary || {}

  const matched = schemes.filter(s =>
    s.verdict === 'likely_qualifies' || s.verdict === 'possibly_qualifies'
  )
  const unlikely = schemes.filter(s => s.verdict === 'unlikely_to_qualify')

  // Override schemes_to_apply with only matched ones (not all 8)
  const matchedHandoff = {
    ...handoff,
    schemes_to_apply: matched.map(s => s.scheme_name || s.scheme_id),
  }


  return (
    <div className="results-outer">
      <div className="results-inner">

        {/* Summary bar */}
        <div className="summary-bar">
          <div className="summary-stat">
            <span className="stat-num matched">{matched.length}</span>
            <span className="stat-label">{lang === 'hi' ? 'योजनाएं मिलीं' : 'Schemes matched'}</span>
          </div>
          <div className="summary-divider" />
          <div className="summary-stat">
            <span className="stat-num">{schemes.length}</span>
            <span className="stat-label">{lang === 'hi' ? 'कुल जांची' : 'Total checked'}</span>
          </div>
          <div className="summary-divider" />
          <div className="summary-stat">
            <span className="stat-num docs">{documents.length}</span>
            <span className="stat-label">{lang === 'hi' ? 'दस्तावेज़' : 'Documents needed'}</span>
          </div>
        </div>

        <SummaryBanner summary={stackingSummary} lang={lang} />

        {/* Matched schemes */}
        {matched.length > 0 && (
          <section className="results-section">
            <h2 className="section-heading">
              ✅ {lang === 'hi' ? 'आप इन योजनाओं के लिए पात्र हो सकते हैं' : 'You likely qualify for these schemes'}
            </h2>
            <div className="cards-grid">
              {matched.map((s, i) => (
                <div key={i}>
                  <ResultCard scheme={s} lang={lang} />
                  {s.reasoning_chain?.length > 0 && (
                    <ReasoningChain chain={s.reasoning_chain} lang={lang} />
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Documents */}
        {documents.length > 0 && (
          <section className="results-section">
            <h2 className="section-heading">
              📋 {lang === 'hi' ? 'आवश्यक दस्तावेज़' : 'Documents to bring to CSC'}
            </h2>
            <DocumentChecklist documents={documents} lang={lang} />
          </section>
        )}

        {/* Handoff */}
        {(handoff.handoff_summary || handoff.csc_instruction) && (
          <section className="results-section">
            <h2 className="section-heading">
              🏢 {lang === 'hi' ? 'CSC पर जाएं' : 'Go to your nearest CSC'}
            </h2>
            <HandoffCard handoff={matchedHandoff} lang={lang} />
          </section>
        )}

        {/* Unlikely schemes */}
        {unlikely.length > 0 && (
          <section className="results-section">
            <h2 className="section-heading dim">
              ✗ {lang === 'hi' ? 'इन योजनाओं के लिए पात्र नहीं' : 'Unlikely to qualify'}
            </h2>
            <div className="unlikely-list">
              {unlikely.map((s, i) => (
                <div key={i} className="unlikely-item">
                  <span>{s.scheme_name}</span>
                  <span className="unlikely-reason">
                    {s.reasoning_chain?.[0]?.explanation || ''}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        <div className="disclaimer-box">
          ⚠️ {lang === 'hi'
            ? 'यह एआई पूर्ण पात्रता की पुष्टि नहीं करता। अंतिम सत्यापन CSC VLE द्वारा होगा।'
            : 'This AI does not confirm final eligibility. Aadhaar verification and final application must be completed at a Common Service Centre (CSC) by a VLE.'}
        </div>
      </div>
    </div>
  )
}
