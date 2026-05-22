import { useNavigate } from 'react-router-dom'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { DatesSetArg, EventInput } from '@fullcalendar/core'
import { useState } from 'react'
import client from '../api/client'

export function CalendarPage() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<EventInput[]>([])

  const handleDatesSet = async (info: DatesSetArg) => {
    // Use midpoint of the visible range so timezone offset never shifts the month.
    const mid = new Date((info.start.getTime() + info.end.getTime()) / 2)
    const month = `${mid.getFullYear()}-${String(mid.getMonth() + 1).padStart(2, '0')}`
    try {
      const resp = await client.get('/calendar', { params: { month } })
      // TODO Task-3: render emotion emoji per entry
      const dates: string[] = resp.data.entries.map((e: { date: string; emotion: string }) => e.date)
      setEvents(dates.map((d) => ({ id: d, title: '일기 확인', start: d, allDay: true })))
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
        events={events}
        datesSet={handleDatesSet}
        height="auto"
        eventContent={(info) => (
          <button
            onClick={(e) => {
              e.stopPropagation()
              navigate(`/diary/${info.event.id}`)
            }}
            style={{
              background: '#4f46e5',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              padding: '2px 8px',
              fontSize: 11,
              cursor: 'pointer',
              width: '100%',
              textAlign: 'center',
            }}
          >
            일기 확인
          </button>
        )}
      />
    </div>
  )
}
