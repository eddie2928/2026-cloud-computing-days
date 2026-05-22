import { describe, it, expect } from 'vitest'
import { getWeekWindow } from '../src/lib/week'
import { searchEntries } from '../src/lib/search'
import { getStreak } from '../src/lib/streak'

const MAY_ENTRIES = Array.from({ length: 31 }, (_, i) => ({
  date: `2026-05-${String(i + 1).padStart(2, '0')}`,
  emotion: 'happy',
}))

describe('lib/week', () => {
  it('today=15일 일 때 length=7, 가운데(index 3)가 15일', () => {
    const result = getWeekWindow(MAY_ENTRIES, '2026-05-15')
    expect(result).toHaveLength(7)
    expect(result[3].date).toBe('2026-05-15')
  })

  it('항목 없는 날은 emotion이 undefined', () => {
    const result = getWeekWindow([], '2026-05-15')
    expect(result).toHaveLength(7)
    result.forEach(d => expect(d.emotion).toBeUndefined())
  })
})

describe('lib/search', () => {
  it("q='05-2' → '2026-05-2x' 항목만 반환", () => {
    const result = searchEntries(MAY_ENTRIES, '05-2')
    expect(result.every(e => e.date.includes('05-2'))).toBe(true)
    expect(result.length).toBeGreaterThan(0)
  })

  it('q=빈 문자열 → 빈 배열', () => {
    expect(searchEntries(MAY_ENTRIES, '')).toHaveLength(0)
  })
})

describe('lib/streak', () => {
  it('오늘 항목 없으면 streak=0 (단절)', () => {
    const yesterday = '2026-05-14'
    const today = '2026-05-15'
    const entries = [{ date: yesterday, emotion: 'happy' }]
    expect(getStreak(entries, today)).toBe(0)
  })

  it('오늘부터 연속 3일 있으면 streak=3', () => {
    const entries = [
      { date: '2026-05-13', emotion: 'happy' },
      { date: '2026-05-14', emotion: 'neutral' },
      { date: '2026-05-15', emotion: 'sad' },
    ]
    expect(getStreak(entries, '2026-05-15')).toBe(3)
  })

  it('오늘만 있으면 streak=1', () => {
    expect(getStreak([{ date: '2026-05-15' }], '2026-05-15')).toBe(1)
  })
})
