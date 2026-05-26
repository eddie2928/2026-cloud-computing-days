import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { MonthGrid } from '../components/calendar/MonthGrid'
import { type CalendarEntry, type HolidayItem, type ScheduleItem } from '../lib/week'

const now = new Date()

export function Calendar() {
  const navigate = useNavigate()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [entries, setEntries] = useState<CalendarEntry[]>([])
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [holidays, setHolidays] = useState<HolidayItem[]>([])

  const fetchCalendar = useCallback(() => {
    const m = `${year}-${String(month).padStart(2, '0')}`
    client.get(`/calendar?month=${m}`).then(res => {
      setEntries(res.data.entries ?? [])
      setSchedules(res.data.schedules ?? [])
      setHolidays(res.data.holidays ?? [])
    }).catch(() => {})
  }, [year, month])

  useEffect(() => {
    fetchCalendar()
  }, [fetchCalendar])

  const goPrev = () => {
    if (month === 1) { setYear(y => y - 1); setMonth(12) }
    else setMonth(m => m - 1)
  }

  const goNext = () => {
    if (month === 12) { setYear(y => y + 1); setMonth(1) }
    else setMonth(m => m + 1)
  }

  return (
    <div style={{ padding: '8px 16px' }}>
      <MonthGrid
        year={year}
        month={month}
        entries={entries}
        schedules={schedules}
        holidays={holidays}
        onPrev={goPrev}
        onNext={goNext}
        onCellClick={date => {
          if (entries.some(e => e.date === date)) navigate(`/diary/${date}`)
          else navigate(`/qna/${date}`)
        }}
        onScheduleClick={s => navigate(`/schedule/${s.id}`)}
      />
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12, marginBottom: 8 }}>
        <button
          onClick={() => navigate('/schedule/new')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '9px 20px',
            borderRadius: 999,
            border: '1.5px solid var(--sage-leaf)',
            background: 'transparent',
            color: 'var(--sage-forest)',
            fontFamily: 'var(--font-sans)',
            fontWeight: 500,
            fontSize: 14,
            cursor: 'pointer',
          }}
        >
          <span style={{ fontSize: 16, lineHeight: 1 }}>+</span>
          일정 추가
        </button>
      </div>
    </div>
  )
}
