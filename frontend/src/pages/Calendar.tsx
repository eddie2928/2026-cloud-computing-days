import { useState, useEffect } from 'react'
import client from '../api/client'
import { MonthGrid } from '../components/calendar/MonthGrid'
import { type CalendarEntry } from '../lib/week'
import { useDayModal } from '../hooks/dayModalContext'

const now = new Date()

export function Calendar() {
  const { openDayModal } = useDayModal()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [entries, setEntries] = useState<CalendarEntry[]>([])

  useEffect(() => {
    const m = `${year}-${String(month).padStart(2, '0')}`
    client.get(`/calendar?month=${m}`).then(res => {
      setEntries(res.data.entries ?? [])
    }).catch(() => {})
  }, [year, month])

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
        onPrev={goPrev}
        onNext={goNext}
        onCellClick={date => openDayModal(date)}
      />
    </div>
  )
}
