import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { postChat } from '../api/client'
import type { ChatRequest, ChatResponse, WindowQuery } from '../api/types'
import { formatTime } from '../dates'
import { DemoBadge } from './Common'

interface Exchange { question: string; response: ChatResponse }

export function Assistant({ window }: { window: WindowQuery | null }) {
  const [message, setMessage] = useState('')
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<ChatRequest | null>(null)
  // A ref remembers the current request without causing a render. Component
  // state, in contrast, stores values that should change what the user sees.
  const currentRequest = useRef<AbortController | null>(null)
  useEffect(() => () => currentRequest.current?.abort(), [])

  async function send(body: ChatRequest) {
    currentRequest.current?.abort()
    const controller = new AbortController()
    currentRequest.current = controller
    setPending(true)
    setError(null)
    setLastRequest(body)
    try {
      const response = await postChat(body, controller.signal)
      if (controller.signal.aborted || currentRequest.current !== controller) return
      setExchanges((previous) => [...previous, {
        question: body.request_type === 'weekly_summary' ? 'Request a weekly summary' : body.message ?? '',
        response,
      }])
      setMessage('')
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Assistant request failed.')
    } finally {
      if (!controller.signal.aborted && currentRequest.current === controller) setPending(false)
    }
  }

  function submit(event: FormEvent) {
    // A normal HTML form would navigate to a new document. Prevent that here:
    // fetch JSON, update React state, and keep the surrounding dashboard mounted.
    event.preventDefault()
    if (window && message.trim()) void send({ ...window, request_type: 'chat', message: message.trim() })
  }

  return <section aria-labelledby="assistant-title">
    <div className="section-heading">
      <div>
        <p className="eyebrow">A place for questions</p>
        <h2 id="assistant-title">Assistant</h2>
      </div>
      <DemoBadge show={exchanges.some((exchange) => exchange.response.is_demo)} />
    </div>

    <div className="assistant-grid">
      <div className="panel assistant-panel">
        <div className="assistant-intro">
          <span className="assistant-icon" aria-hidden="true">✳</span>
          <div>
            <h3>Energy assistant preview</h3>
            <p>This mock endpoint returns placeholders. Bedrock is not connected; no AI insights or citations are generated.</p>
          </div>
        </div>
        
        <div className="conversation" role="log" aria-label="Assistant conversation" aria-live="polite">
          {exchanges.length === 0 && <p className="empty-conversation">Ask a question about your selected historical period, or try the weekly-summary request.</p>}
          {exchanges.map((exchange, index) => <div className="exchange" key={index}>
            <p className="user-message"><strong>You</strong>{exchange.question}</p>
            <div className="assistant-message">
              <div>
                <strong>Assistant · {exchange.response.status}</strong>
                <DemoBadge show={exchange.response.is_demo} />
              </div>
              
              <p>{exchange.response.answer}</p>
              <small>{exchange.response.assistant_connected ? 'Assistant connected' : 'Assistant disconnected'} · {formatTime(exchange.response.requested_start)} → {formatTime(exchange.response.requested_end)} UTC (end exclusive)</small>
              {exchange.response.citations.length === 0 && <p className="muted">No citations returned.</p>}
            </div>
          </div>)}

          {pending && <p className="notice" role="status">Waiting for the mock API…</p>}
        </div>

        {error && <div className="notice error" role="alert"><p>{error}</p><button disabled={pending} onClick={() => { if (lastRequest) void send(lastRequest) }}>Retry request</button></div>}
        
        <form className="chat-form" onSubmit={submit}>
          <label htmlFor="question">Your question</label>
          <textarea id="question" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Why was usage high this week?" maxLength={2000} rows={3} disabled={pending || !window} />
          <div>
            <small>{message.length}/2000 characters</small>
            <button className="primary-button" type="submit" disabled={pending || !window || !message.trim()}>Send question <span aria-hidden="true">↗</span>
            </button>
          </div>
        </form>

      </div>

      <aside className="panel summary-panel">
        <p className="eyebrow">The bigger picture</p>
        <h3>Weekly summary</h3>
        <p>Send your selected period to the same mock API using the weekly-summary contract.</p>
        <p>This is a placeholder request for the assistant integration, not a generated report.</p>
        <button disabled={pending || !window} onClick={() => { if (window) void send({ ...window, request_type: 'weekly_summary' }) }}>Request weekly summary</button>
        <small>The response will appear in the conversation.</small>
      </aside>

    </div>
  </section>
}
