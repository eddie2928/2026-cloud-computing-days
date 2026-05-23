import { useState, useEffect } from 'react'
import client from '../api/client'
import { WeekStrip } from '../components/hub/WeekStrip'
import { TodayDiaryCard } from '../components/hub/TodayDiaryCard'
import { SearchTriggerCard } from '../components/hub/SearchTriggerCard'
import { PetCard } from '../components/hub/PetCard'
import { SearchModal } from '../components/search/SearchModal'
import { getWeekWindow, type CalendarEntry } from '../lib/week'
import { fetchStreak } from '../lib/streak'
import { useDayModal } from '../hooks/dayModalContext'

const TODAY = new Date().toISOString().split('T')[0]
const THIS_MONTH = TODAY.slice(0, 7)

export function Hub() {
  const { openDayModal } = useDayModal()
  const [entries, setEntries] = useState<CalendarEntry[]>([])
  const [diaryBody, setDiaryBody] = useState<string | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [streak, setStreak] = useState<number | null>(null)

  useEffect(() => {
    client.get(`/calendar?month=${THIS_MONTH}`).then(res => {
      setEntries(res.data.entries ?? [])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    client.get(`/diary/${TODAY}`).then(res => {
      setDiaryBody(res.data.body ?? '')
    }).catch(() => {
      setDiaryBody(null)
    })
  }, [])

  useEffect(() => {
    fetchStreak().then(setStreak).catch(() => setStreak(null))
  }, [])

  const weekDays = getWeekWindow(entries, TODAY)
  const hasDiary = diaryBody !== null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, padding: '16px 16px 8px' }}>
      {streak !== null && streak > 0 && (
        <div style={{ textAlign: 'center', fontSize: '1.1rem', fontWeight: 600, color: 'var(--sage-leaf)' }}>
          🔥 {streak}일 연속
        </div>
      )}
      <WeekStrip days={weekDays} today={TODAY} />

      <div style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>
        <TodayDiaryCard
          today={TODAY}
          hasDiary={hasDiary}
          summary={diaryBody ?? undefined}
          onOpen={openDayModal}
        />
        <SearchTriggerCard onClick={() => setSearchOpen(true)} />
      </div>

      <PetCard />

      {searchOpen && (
        <SearchModal
          onClose={() => setSearchOpen(false)}
          onSelect={(date) => {
            setSearchOpen(false)
            openDayModal(date)
          }}
        />
      )}
    </div>
  )
}
