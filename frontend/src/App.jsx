import { useState } from 'react'
import Chat from './components/Chat.jsx'
import ResultsPage from './components/ResultsPage.jsx'
import './App.css'

export default function App() {
  const [phase, setPhase] = useState('chat') // 'chat' | 'results'
  const [results, setResults] = useState(null)
  const [lang, setLang] = useState('en')

  function handleResults(data) {
    setResults(data)
    setPhase('results')
  }

  function handleRestart() {
    setResults(null)
    setPhase('chat')
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">🇮🇳</span>
            <div>
              <span className="logo-title">YojanaPath</span>
              <span className="logo-sub">योजना पाथ</span>
            </div>
          </div>
          <div className="header-right">
            <button
              className={`lang-btn ${lang === 'en' ? 'active' : ''}`}
              onClick={() => setLang('en')}
            >EN</button>
            <button
              className={`lang-btn ${lang === 'hi' ? 'active' : ''}`}
              onClick={() => setLang('hi')}
            >हि</button>
            {phase === 'results' && (
              <button className="restart-btn" onClick={handleRestart}>
                ↩ {lang === 'hi' ? 'दोबारा शुरू करें' : 'Start Over'}
              </button>
            )}
          </div>
        </div>
      </header>

      {phase === 'chat' && (
        <Chat onResults={handleResults} lang={lang} />
      )}
      {phase === 'results' && results && (
        <ResultsPage data={results} lang={lang} />
      )}

      <footer className="app-footer">
        <p>⚠️ {lang === 'hi'
          ? 'यह एआई केवल मार्गदर्शन के लिए है। अंतिम पात्रता CSC VLE द्वारा सत्यापित की जाएगी।'
          : 'AI guidance only. Final eligibility is verified by a CSC Village Level Entrepreneur (VLE). No data is stored.'
        }</p>
      </footer>
    </div>
  )
}
