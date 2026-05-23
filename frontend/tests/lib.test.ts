import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { getWeekWindow } from '../src/lib/week'
import { searchDiaries } from '../src/lib/search'
import { fetchStreak } from '../src/lib/streak'

const MAY_ENTRIES = Array.from({ length: 31 }, (_, i) => ({
  date: `2026-05-${String(i + 1).padStart(2, '0')}`,
  emotion: 'happy',
}))

const server = setupServer(
  http.get('/api/user/streak', () => HttpResponse.json({ streak: 5 })),
  http.get('/api/diary/search', ({ request }) => {
    const q = new URL(request.url).searchParams.get('q') ?? ''
    if (!q) return HttpResponse.json({ results: [] })
    return HttpResponse.json({
      results: [
        { date: '2026-05-15', snippet: `...${q}...`, emotion: 'happy' },
      ],
    })
  }),
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
  it('searchDiaries(q) returns results from API', async () => {
    const results = await searchDiaries('산책')
    expect(results).toHaveLength(1)
    expect(results[0].snippet).toContain('산책')
    expect(results[0].date).toBe('2026-05-15')
  })

  it('searchDiaries("") returns empty without API call', async () => {
    const results = await searchDiaries('')
    expect(results).toHaveLength(0)
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
