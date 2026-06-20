import './SummaryBanner.css'

export default function SummaryBanner({ summary, lang }) {
  const annual = summary?.total_annual_cash || 0
  const recurring = summary?.recurring_benefits || []
  const recurringText = recurring.length
    ? recurring.join(' • ')
    : (lang === 'hi' ? 'कोई recurring in-kind लाभ नहीं मिला' : 'No recurring in-kind benefits found')

  return (
    <section className="summary-banner">
      <div className="summary-banner__eyebrow">
        {lang === 'hi' ? 'कुल अनुमानित मूल्य' : 'Estimated combined value'}
      </div>
      <div className="summary-banner__amount">
        ₹{annual.toLocaleString('en-IN')}
        <span>{lang === 'hi' ? ' इस वर्ष' : ' this year'}</span>
      </div>
      <p className="summary-banner__text">
        {lang === 'hi'
          ? `Combined, आपको ₹${annual.toLocaleString('en-IN')} इस वर्ष मिल सकते हैं, plus ${recurringText}`
          : `Combined, you could receive ₹${annual.toLocaleString('en-IN')} this year, plus ${recurringText}`}
      </p>
    </section>
  )
}
