import { useNavigate } from 'react-router-dom'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventInput, DatesSetArg } from '@fullcalendar/core'
import type { DateClickArg } from '@fullcalendar/interaction'
import { useState } from 'react'
import client from '../api/client'

export function CalendarPage() {
  const navigate = useNavigate()
  const [events, setEvents] = useState<EventInput[]>([])

  const handleDatesSet = async (info: DatesSetArg) => {
    const month = info.start.toISOString().slice(0, 7)
    try {
      const resp = await client.get('/calendar', { params: { month } })
      const dates: string[] = resp.data.dates
      setEvents(dates.map((d) => ({ title: '일기', date: d, display: 'dot' })))
    } catch {
      // ignore
    }
  }

  const handleDateClick = (info: DateClickArg) => {
    navigate(`/diary/${info.dateStr}`)
  }

  return (
    <div style={{ padding: 24 }}>
      <h2>캘린더</h2>
      <FullCalendar
        plugins={[dayGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        events={events}
        datesSet={handleDatesSet}
        dateClick={handleDateClick}
        height="auto"
      />
    </div>
  )
}
