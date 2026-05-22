import { useEffect, useRef, useState } from 'react'
import client from '../../api/client'
import { ChatBubble } from '../qna/ChatBubble'
import { ThinkingDots } from '../qna/ThinkingDots'
import { ChatInput } from '../qna/ChatInput'
import { ProgressBar } from '../days/ProgressBar'

interface Message {
  role: 'ai' | 'user'
  text: string
}

interface QnaModalContentProps {
  date: string
  onComplete: () => void
}

const TOTAL = 5

export function QnaModalContent({ date, onComplete }: QnaModalContentProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sequence, setSequence] = useState(0)
  const [thinking, setThinking] = useState(false)
  const [done, setDone] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    client
      .post('/qna/start', { diary_date: date })
      .then((res) => {
        setSessionId(res.data.session_id)
        setSequence(res.data.sequence)
        setMessages([{ role: 'ai', text: res.data.question }])
      })
      .catch(() => {})
  }, [date])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const handleSend = async (text: string) => {
    if (!sessionId || thinking || done) return
    setMessages((m) => [...m, { role: 'user', text }])
    setThinking(true)
    try {
      const res = await client.post('/qna/answer', {
        session_id: sessionId,
        sequence,
        answer: text,
      })
      setThinking(false)
      if (res.data.completed) {
        setDone(true)
        onComplete()
      } else {
        setSequence(res.data.sequence)
        setMessages((m) => [...m, { role: 'ai', text: res.data.next_question }])
      }
    } catch {
      setThinking(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: 460 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-xs)', color: 'var(--ink-meta)' }}>
            {date} · {sequence} / {TOTAL}
          </span>
        </div>
        <ProgressBar value={sequence} max={TOTAL} />
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          padding: '4px 2px',
        }}
      >
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role}>
            {msg.text}
          </ChatBubble>
        ))}
        {thinking && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <ThinkingDots visible />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div>
        <ChatInput onSend={handleSend} disabled={thinking || done} />
      </div>
    </div>
  )
}
