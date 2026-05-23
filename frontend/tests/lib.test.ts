import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { getWeekWindow } from '../src/lib/week'
import { searchEntries } from '../src/lib/search'
import { fetchStreak } from '../src/lib/streak'

const MAY_ENTRIES = Array.from({ length: 31 }, (_, i) => ({
  date: `2026-05-${String(i + 1).padStart(2, '0')}`,
  emotion: 'happy',
}))

const server = setupServer(
  http.get('/api/user/streak', () => HttpResponse.json({ streak: 5 }))
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

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
  it('fetchStreak() returns streak from API', async () => {
    const streak = await fetchStreak()
    expect(streak).toBe(5)
  })

  it('fetchStreak() returns 0 when API returns 0', async () => {
    server.use(http.get('/api/user/streak', () => HttpResponse.json({ streak: 0 })))
    const streak = await fetchStreak()
    expect(streak).toBe(0)
  })
})
