import './DocumentChecklist.css'

export default function DocumentChecklist({ documents, lang }) {
  return (
    <div className="doc-list">
      {documents.map((doc, i) => (
        <div key={i} className="doc-item">
          <div className="doc-icon">📄</div>
          <div className="doc-content">
            <span className="doc-name">{doc.document}</span>
            {doc.required_for?.length > 0 && (
              <div className="doc-schemes">
                {doc.required_for.map((s, j) => (
                  <span key={j} className="doc-scheme-tag">{s}</span>
                ))}
              </div>
            )}
            {doc.flag && (
              <div className="doc-flag">⚠️ {doc.flag}</div>
            )}
          </div>
          <div className="doc-check">☐</div>
        </div>
      ))}
    </div>
  )
}
