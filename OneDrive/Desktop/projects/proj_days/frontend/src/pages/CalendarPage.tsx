import { useNavigate } from 'react-router-dom'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { DatesSetArg } from '@fullcalendar/core'
import { useState } from 'react'
import client from '../api/client'

export function CalendarPage() {
  const navigate = useNavigate()
  const [diaryDates, setDiaryDates] = useState<Set<string>>(new Set())

  const handleDatesSet = async (info: DatesSetArg) => {
    const month = info.start.toISOString().slice(0, 7)
    try {
      const resp = await client.get('/calendar', { params: { month } })
      const dates: string[] = resp.data.dates
      setDiaryDates(new Set(dates))
    } catch {
      // ignore
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 860, margin: '0 auto' }}>
      <h2>캘린더</h2>
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        datesSet={handleDatesSet}
        height="auto"
        dayCellContent={(arg) => {
          const dateStr = arg.date.toISOString().slice(0, 10)
          const hasDiary = diaryDates.has(dateStr)
          return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, padding: '2px 4px' }}>
              <span>{arg.dayNumberText}</span>
              {hasDiary && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/diary/${dateStr}`)
                  }}
                  style={{
                    background: '#4f46e5',
                    color: 'white',
                    border: 'none',
                    borderRadius: 5,
                    padding: '2px 7px',
                    fontSize: 11,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                >
                  일기 확인
                </button>
              )}
            </div>
          )
        }}
      />
    </div>
  )
}
