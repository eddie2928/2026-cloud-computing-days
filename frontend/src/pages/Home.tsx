import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { DatesSetArg, EventInput } from '@fullcalendar/core'
import type { DateClickArg } from '@fullcalendar/interaction'
import client from '../api/client'
import { EMOTION_EMOJI, type EmotionKey } from '../lib/emotions'
import { DiaryDetailModal } from '../components/DiaryDetailModal'
import { ChatSessionModal } from '../components/ChatSessionModal'

interface CalendarEntry {
  date: string
  emotion: string
}

export function Home() {
  const [entries, setEntries] = useState<CalendarEntry[]>([])
  const [selectedDiaryDate, setSelectedDiaryDate] = useState<string | null>(null)
  const [selectedNewDate, setSelectedNewDate] = useState<string | null>(null)

  const fetchCalendar = useCallback(async (month: string) => {
    try {
      const resp = await client.get('/calendar', { params: { month } })
      setEntries(resp.data.entries)
    } catch {
      // ignore
    }
  }, [])

  const handleDatesSet = async (info: DatesSetArg) => {
    const mid = new Date((info.start.getTime() + info.end.getTime()) / 2)
    const month = `${mid.getFullYear()}-${String(mid.getMonth() + 1).padStart(2, '0')}`
    await fetchCalendar(month)
  }

  const handleDateClick = (info: DateClickArg) => {
    const dateStr = info.dateStr
    const entry = entries.find((e) => e.date === dateStr)
    if (entry) {
      setSelectedDiaryDate(dateStr)
    } else {
      setSelectedNewDate(dateStr)
    }
  }

  const events: EventInput[] = entries.map((e) => ({
    id: e.date,
    start: e.date,
    allDay: true,
    extendedProps: { emotion: e.emotion },
    display: 'background',
  }))

  const handleDiaryUpdated = useCallback(() => {
    // 캘린더 데이터를 다시 불러오기 위해 entries를 초기화 후 재조회
    // FullCalendar가 datesSet을 다시 호출하도록 강제하기는 어려우므로
    // entries를 직접 갱신하는 방식으로 처리
    setEntries((prev) => [...prev])
  }, [])

  const handleChatComplete = useCallback(async () => {
    if (!selectedNewDate) return
    const date = selectedNewDate
    setSelectedNewDate(null)
    // 새 일기가 생성됐으므로 캘린더 재조회
    try {
      const mid = new Date(date)
      const month = `${mid.getFullYear()}-${String(mid.getMonth() + 1).padStart(2, '0')}`
      const resp = await client.get('/calendar', { params: { month } })
      setEntries(resp.data.entries)
    } catch {
      // ignore
    }
    // 생성된 날짜의 일기를 바로 열기
    setSelectedDiaryDate(date)
  }, [selectedNewDate])

  return (
    <div style={{ minHeight: '100vh', background: '#fafafa' }}>
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 24px',
        background: 'white',
        borderBottom: '1px solid #e5e7eb',
      }}>
        <span style={{ fontWeight: 700, fontSize: 20, color: '#4f46e5', letterSpacing: '-0.5px' }}>Days</span>
        <Link to="/profile" aria-label="프로필" style={{ fontSize: 24, textDecoration: 'none' }}>👤</Link>
      </header>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px' }}>
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          events={events}
          datesSet={handleDatesSet}
          dateClick={handleDateClick}
          height="auto"
          eventContent={(info) => {
            const emotion = info.event.extendedProps.emotion as EmotionKey
            return (
              <div style={{ textAlign: 'center', fontSize: 22, pointerEvents: 'none' }}>
                {EMOTION_EMOJI[emotion] ?? ''}
              </div>
            )
          }}
          dayCellClassNames={() => 'fc-day-clickable'}
        />
      </div>

      <DiaryDetailModal
        date={selectedDiaryDate}
        onClose={() => setSelectedDiaryDate(null)}
        onUpdated={handleDiaryUpdated}
      />

      <ChatSessionModal
        date={selectedNewDate}
        onClose={() => setSelectedNewDate(null)}
        onComplete={handleChatComplete}
      />
    </div>
  )
}
