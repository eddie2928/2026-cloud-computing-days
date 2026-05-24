import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Header } from '../components/layout/Header'
import { ChatBubble } from '../components/qna/ChatBubble'
import { ThinkingDots } from '../components/qna/ThinkingDots'
import { ChatInput } from '../components/qna/ChatInput'
import { ProgressBar } from '../components/days/ProgressBar'
import { ScheduleCard } from '../components/qna/ScheduleCard'

interface Message {
  role: 'ai' | 'user'
  text: string
}

interface PendingSchedule {
  period_start: string
  period_end: string
  situation: string
}

function scheduleKey(s: PendingSchedule) {
  return `${s.period_start}_${s.period_end}_${s.situation}`
}

export function Qna() {
  const { date } = useParams<{ date: string }>()
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([])
  const [pendingByMsgIdx, setPendingByMsgIdx] = useState<Map<number, PendingSchedule[]>>(new Map())
  const [scheduleStatuses, setScheduleStatuses] = useState<Map<string, 'pending' | 'accepted' | 'rejected'>>(new Map())
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
      const aiMsgIdx = 0
      setMessages([{ role: 'ai', text: res.data.question }])
      const pending: PendingSchedule[] = res.data.pending_schedules ?? []
      if (pending.length > 0) {
        setPendingByMsgIdx(prev => new Map(prev).set(aiMsgIdx, pending))
        setScheduleStatuses(prev => {
          const next = new Map(prev)
          for (const s of pending) next.set(scheduleKey(s), 'pending')
          return next
        })
      }
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
        setMessages(m => {
          const next = [...m, { role: 'ai' as const, text: res.data.next_question }]
          const aiMsgIdx = next.length - 1
          const pending: PendingSchedule[] = res.data.pending_schedules ?? []
          if (pending.length > 0) {
            setPendingByMsgIdx(prev => new Map(prev).set(aiMsgIdx, pending))
            setScheduleStatuses(prev => {
              const statuses = new Map(prev)
              for (const s of pending) statuses.set(scheduleKey(s), 'pending')
              return statuses
            })
          }
          return next
        })
      }
    } catch {
      setThinking(false)
    }
  }

  const handleAccept = async (s: PendingSchedule) => {
    const key = scheduleKey(s)
    try {
      await client.post('/schedules', {
        period_start: s.period_start,
        period_end: s.period_end,
        situation: s.situation,
      })
    } catch {
      // 409 중복은 무시
    }
    setScheduleStatuses(prev => new Map(prev).set(key, 'accepted'))
  }

  const handleReject = (s: PendingSchedule) => {
    setScheduleStatuses(prev => new Map(prev).set(scheduleKey(s), 'rejected'))
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
          <div key={i}>
            <ChatBubble role={msg.role}>{msg.text}</ChatBubble>
            {msg.role === 'ai' && (pendingByMsgIdx.get(i) ?? []).map(s => (
              <ScheduleCard
                key={scheduleKey(s)}
                schedule={s}
                status={scheduleStatuses.get(scheduleKey(s)) ?? 'pending'}
                onAccept={() => handleAccept(s)}
                onReject={() => handleReject(s)}
              />
            ))}
          </div>
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
