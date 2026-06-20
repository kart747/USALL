import './Message.css'

export default function Message({ msg }) {
  const isBot = msg.role === 'bot'
  return (
    <div className={`message ${isBot ? 'bot' : 'user'}`}>
      {isBot && <div className="msg-avatar">🤖</div>}
      <div className={`msg-bubble ${isBot ? 'bot-bubble' : 'user-bubble'}`}>
        {msg.text}
      </div>
    </div>
  )
}
