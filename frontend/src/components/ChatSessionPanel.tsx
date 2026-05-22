import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import client from '../api/client'
import Spinner from './Spinner'

type Phase = 'idle' | 'thinking' | 'finalizing'

interface Message {
  role: 'ai' | 'user'
  text: string
  seq?: number
}

interface QnAState {
  sessionId: number
  sequence: number
}

interface Props {
  date: string
  onComplete: (diaryBody: string) => void
  onClose: () => void
}

const bubble: Record<'ai' | 'user', React.CSSProperties> = {
  ai: {
    maxWidth: '70%',
    padding: '10px 14px',
    borderRadius: '0 16px 16px 16px',
    background: '#f3f4f6',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
  },
  user: {
    maxWidth: '70%',
    padding: '10px 14px',
    borderRadius: '16px 0 16px 16px',
    background: '#e8f4fd',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap',
  },
}

const avatar: React.CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: '50%',
  background: '#d1d5db',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 12,
  fontWeight: 600,
  color: '#374151',
  flexShrink: 0,
}

export function ChatSessionPanel({ date, onComplete }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [qnaState, setQnaState] = useState<QnAState | null>(null)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [completed, setCompleted] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, phase])

  // 마운트 시 자동으로 세션 시작
  useEffect(() => {
    let cancelled = false
    setPhase('thinking')
    client.post('/qna/start', { diary_date: date })
      .then((resp) => {
        if (cancelled) return
        const data = resp.data
        setQnaState({ sessionId: data.session_id, sequence: data.sequence })
        const history: Array<{ sequence: number; question: string; answer: string }> = data.history ?? []
        const historyMessages: Message[] = history.flatMap((h) => ([
          { role: 'ai' as const, text: h.question, seq: h.sequence },
          { role: 'user' as const, text: h.answer },
        ]))
        setMessages([...historyMessages, { role: 'ai', text: data.question, seq: data.sequence }])
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 409) {
          setError('이미 완료된 날짜입니다.')
          setCompleted(true)
        } else {
          setError('오류가 발생했습니다.')
        }
      })
      .finally(() => {
        if (!cancelled) setPhase('idle')
      })
    return () => { cancelled = true }
  }, [date])

  const handleAnswer = async (e: FormEvent) => {
    e.preventDefault()
    if (!qnaState || !answer.trim() || phase !== 'idle') return
    setError('')
    const submittedAnswer = answer.trim()
    setAnswer('')
    setMessages((prev) => [...prev, { role: 'user', text: submittedAnswer }])
    const isFinal = qnaState.sequence >= 5
    setPhase(isFinal ? 'finalizing' : 'thinking')
    try {
      const resp = await client.post('/qna/answer', {
        session_id: qnaState.sessionId,
        sequence: qnaState.sequence,
        answer: submittedAnswer,
      })
      const data = resp.data

      if (data.completed) {
        setPhase('idle')
        setCompleted(true)
        onComplete(data.diary ?? '')
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'ai', text: data.next_question, seq: data.sequence },
        ])
        setQnaState({ ...qnaState, sequence: data.sequence })
        setPhase('idle')
      }
    } catch {
      setError('답변 제출 중 오류가 발생했습니다.')
      setMessages((prev) => prev.slice(0, -1))
      setAnswer(submittedAnswer)
      setPhase('idle')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAnswer(e as unknown as FormEvent)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '60vh', minHeight: 400 }}>
      <div style={{ padding: '0 0 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 600, fontSize: 15, marginBottom: 12 }}>
        {date} &nbsp;·&nbsp; {qnaState ? `${qnaState.sequence} / 5` : '시작 중...'}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', alignItems: 'flex-start', gap: 8 }}>
            {msg.role === 'ai' && <div style={avatar}>AI</div>}
            <div style={bubble[msg.role]}>{msg.text}</div>
          </div>
        ))}

        {phase === 'thinking' && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <div style={avatar}>AI</div>
            <div style={{ ...bubble.ai, color: '#9ca3af', fontStyle: 'italic' }}>Thinking...</div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {phase === 'finalizing' && (
        <div
          role="status"
          aria-live="polite"
          style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            gap: 12, padding: '24px 16px', background: '#f8f7ff', borderRadius: 12,
            border: '1px solid #e0deff', margin: '8px 0', textAlign: 'center',
          }}
        >
          <Spinner size={32} />
          <p style={{ margin: 0, fontWeight: 600, color: '#4f46e5' }}>✨ 당신의 일기를 만들고 있어요...</p>
          <small style={{ color: '#9ca3af' }}>10초 이상 걸릴 수 있어요</small>
        </div>
      )}

      {error && <p role="alert" style={{ color: '#dc2626', fontSize: 13, marginTop: 8 }}>{error}</p>}

      {!completed && (
        <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: 12, marginTop: 12 }}>
          <form onSubmit={handleAnswer} style={{ display: 'flex', gap: 8 }}>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              disabled={phase !== 'idle' || completed}
              placeholder={phase !== 'idle' ? '' : '답변 입력 (Enter 전송 / Shift+Enter 줄바꿈)'}
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid #d1d5db',
                resize: 'none',
                fontFamily: 'inherit',
                fontSize: 14,
              }}
            />
            <button
              type="submit"
              disabled={!answer.trim() || phase !== 'idle' || completed}
              style={{
                padding: '0 18px',
                borderRadius: 8,
                background: !answer.trim() || phase !== 'idle' ? '#e5e7eb' : '#4f46e5',
                color: !answer.trim() || phase !== 'idle' ? '#9ca3af' : 'white',
                border: 'none',
                cursor: !answer.trim() || phase !== 'idle' ? 'not-allowed' : 'pointer',
                fontSize: 14,
                fontWeight: 600,
                alignSelf: 'stretch',
              }}
            >
              전송
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
