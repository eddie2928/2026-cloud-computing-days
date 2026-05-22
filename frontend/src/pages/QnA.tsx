import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from 'react'
import client from '../api/client'

interface Message {
  role: 'ai' | 'user'
  text: string
  seq?: number
}

interface QnAState {
  sessionId: number
  sequence: number
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

export function QnA() {
  const [date, setDate] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [qnaState, setQnaState] = useState<QnAState | null>(null)
  const [answer, setAnswer] = useState('')
  const [diary, setDiary] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [completed, setCompleted] = useState(false)
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const handleStart = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setThinking(true)
    try {
      const resp = await client.post('/qna/start', { diary_date: date })
      const data = resp.data
      setQnaState({ sessionId: data.session_id, sequence: data.sequence })
      setMessages([{ role: 'ai', text: data.question, seq: data.sequence }])
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 409) {
        setError('이미 완료된 날짜입니다.')
        setCompleted(true)
      } else {
        setError('오류가 발생했습니다.')
      }
    } finally {
      setThinking(false)
    }
  }

  const handleAnswer = async (e: FormEvent) => {
    e.preventDefault()
    if (!qnaState || !answer.trim() || thinking) return
    setError('')
    const submittedAnswer = answer.trim()
    setAnswer('')
    setMessages((prev) => [...prev, { role: 'user', text: submittedAnswer }])
    setThinking(true)
    try {
      const resp = await client.post('/qna/answer', {
        session_id: qnaState.sessionId,
        sequence: qnaState.sequence,
        answer: submittedAnswer,
      })
      const data = resp.data

      const stored = JSON.parse(localStorage.getItem(`qna:${date}`) || '[]')
      localStorage.setItem(
        `qna:${date}`,
        JSON.stringify([...stored, { seq: qnaState.sequence, a: submittedAnswer }])
      )

      if (data.completed) {
        setDiary(data.diary)
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'ai', text: data.next_question, seq: data.sequence },
        ])
        setQnaState({ ...qnaState, sequence: data.sequence })
      }
    } catch {
      setError('답변 제출 중 오류가 발생했습니다.')
      setMessages((prev) => prev.slice(0, -1))
      setAnswer(submittedAnswer)
    } finally {
      setThinking(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAnswer(e as unknown as FormEvent)
    }
  }

  if (diary) {
    return (
      <div style={{ maxWidth: 600, margin: '40px auto', padding: '0 24px 40px' }}>
        <h2 style={{ marginBottom: 12 }}>일기 생성 완료</h2>
        <p style={{ color: '#6b7280', marginBottom: 16 }}>{date}의 일기</p>
        <div style={{
          background: '#f9fafb',
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: 20,
          whiteSpace: 'pre-wrap',
          lineHeight: 1.8,
        }}>
          {diary}
        </div>
      </div>
    )
  }

  if (!qnaState) {
    return (
      <div style={{ maxWidth: 360, margin: '80px auto', padding: '0 24px', textAlign: 'center' }}>
        <h2 style={{ marginBottom: 24 }}>QnA 작성</h2>
        <form onSubmit={handleStart}>
          <input
            type="date"
            aria-label="날짜 선택"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: 8,
              border: '1px solid #d1d5db',
              fontSize: 15,
              boxSizing: 'border-box',
            }}
          />
          {error && <p role="alert" style={{ color: '#dc2626', marginTop: 10, fontSize: 14 }}>{error}</p>}
          <button
            type="submit"
            disabled={!date || completed || thinking}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '12px 0',
              borderRadius: 8,
              background: completed ? '#9ca3af' : '#4f46e5',
              color: 'white',
              border: 'none',
              fontSize: 15,
              cursor: completed || thinking ? 'not-allowed' : 'pointer',
            }}
          >
            {thinking ? 'Thinking...' : completed ? '이미 완료됨' : '시작'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 1px)' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 600, fontSize: 15 }}>
        {date} &nbsp;·&nbsp; {qnaState.sequence} / 5
      </div>

      <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', alignItems: 'flex-start', gap: 8 }}>
            {msg.role === 'ai' && <div style={avatar}>AI</div>}
            <div style={bubble[msg.role]}>{msg.text}</div>
          </div>
        ))}

        {thinking && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
            <div style={avatar}>AI</div>
            <div style={{ ...bubble.ai, color: '#9ca3af', fontStyle: 'italic' }}>Thinking...</div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div style={{ position: 'sticky', bottom: 0, background: 'white', borderTop: '1px solid #e5e7eb', padding: '12px 20px' }}>
        {error && <p role="alert" style={{ color: '#dc2626', fontSize: 13, marginBottom: 8 }}>{error}</p>}
        <form onSubmit={handleAnswer} style={{ display: 'flex', gap: 8 }}>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={thinking}
            placeholder={thinking ? '' : '답변 입력 (Enter 전송 / Shift+Enter 줄바꿈)'}
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
            disabled={!answer.trim() || thinking}
            style={{
              padding: '0 18px',
              borderRadius: 8,
              background: !answer.trim() || thinking ? '#e5e7eb' : '#4f46e5',
              color: !answer.trim() || thinking ? '#9ca3af' : 'white',
              border: 'none',
              cursor: !answer.trim() || thinking ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 600,
              alignSelf: 'stretch',
            }}
          >
            전송
          </button>
        </form>
      </div>
    </div>
  )
}
