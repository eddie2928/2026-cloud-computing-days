import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Header } from '../components/layout/Header'
import { ChatBubble } from '../components/qna/ChatBubble'
import { ThinkingDots } from '../components/qna/ThinkingDots'
import { ChatInput } from '../components/qna/ChatInput'
import { ProgressBar } from '../components/days/ProgressBar'

interface Message {
  role: 'ai' | 'user'
  text: string
}

export function Qna() {
  const { date } = useParams<{ date: string }>()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [sequence, setSequence] = useState(0)
  const [thinking, setThinking] = useState(false)
  const [done, setDone] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!date) return
    client.post('/qna/start', { diary_date: date }).then(res => {
      setSessionId(res.data.session_id)
      setSequence(res.data.sequence)
      setMessages([{ role: 'ai', text: res.data.question }])
    }).catch(() => {})
  }, [date])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const handleSend = async (text: string) => {
    if (!sessionId || thinking || done) return
    setMessages(m => [...m, { role: 'user', text }])
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
        setMessages(m => [...m, { role: 'ai', text: '오늘의 일기가 완성되었어요.' }])
        setTimeout(() => navigate(`/diary/${date}`), 1200)
      } else {
        setSequence(res.data.sequence)
        setMessages(m => [...m, { role: 'ai', text: res.data.next_question }])
      }
    } catch {
      setThinking(false)
    }
  }

  const totalQuestions = 5

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 'calc(100dvh - 80px)' }}>
      <Header title={date ?? ''} showBack />
      <div style={{ padding: '4px 16px 8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-xs)', color: 'var(--ink-meta)' }}>
            {sequence} / {totalQuestions}
          </span>
        </div>
        <ProgressBar value={sequence} max={totalQuestions} />
      </div>

      {/* 채팅 영역 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((msg, i) => (
          <ChatBubble key={i} role={msg.role}>{msg.text}</ChatBubble>
        ))}
        {thinking && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <ThinkingDots visible />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력 바 */}
      <div style={{ padding: '8px 16px 16px', background: 'var(--paper-bone)' }}>
        <ChatInput onSend={handleSend} disabled={thinking || done} />
      </div>
    </div>
  )
}
