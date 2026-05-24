import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/profile', () => {
    return HttpResponse.json({ detail: 'Profile not found' }, { status: 404 })
  }),

  http.put('/api/profile', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json(body)
  }),

  http.post('/api/logout', () => {
    return HttpResponse.json({ ok: true })
  }),

  http.post('/api/login', async ({ request }) => {
    const body = await request.json() as { password: string }
    if (body.password === 'inha-nxt') {
      return HttpResponse.json({ ok: true }, {
        headers: { 'Set-Cookie': 'session=test-token; HttpOnly' },
      })
    }
    return HttpResponse.json({ detail: 'Wrong password' }, { status: 401 })
  }),

  http.get('/api/me', () => {
    return HttpResponse.json({ user_id: 1 })
  }),

  http.post('/api/qna/start', async ({ request }) => {
    await request.json()
    return HttpResponse.json({
      session_id: 1,
      question: '오늘 가장 기억에 남는 일은 무엇인가요?',
      sequence: 1,
      history: [],
      pending_schedules: [],
    })
  }),

  http.post('/api/qna/answer', async ({ request }) => {
    const body = await request.json() as { session_id: number; sequence: number; answer: string }
    if (body.sequence >= 5) {
      return HttpResponse.json({
        completed: true,
        diary: '오늘 하루를 돌아보며 작성된 일기입니다.',
        pending_schedules: [],
      })
    }
    return HttpResponse.json({
      next_question: `다음 질문 ${body.sequence + 1}번입니다.`,
      sequence: body.sequence + 1,
      completed: false,
      pending_schedules: [],
    })
  }),

  http.get('/api/calendar', ({ request }) => {
    const url = new URL(request.url)
    const month = url.searchParams.get('month')
    if (month === '2026-05') {
      return HttpResponse.json({
        entries: [
          { date: '2026-05-01', emotion: 'happy' },
          { date: '2026-05-15', emotion: 'neutral' },
        ],
        schedules: [],
      })
    }
    return HttpResponse.json({ entries: [], schedules: [] })
  }),

  http.get('/api/schedules', ({ request }) => {
    const url = new URL(request.url)
    const month = url.searchParams.get('month')
    if (month === '2026-05') {
      return HttpResponse.json([
        { id: 1, period_start: '2026-05-01', period_end: '2026-05-15', situation: '테스트 일정' },
      ])
    }
    return HttpResponse.json([])
  }),

  http.post('/api/schedules', async ({ request }) => {
    const body = await request.json() as { period_start: string; period_end: string; situation: string }
    return HttpResponse.json({ id: 99, ...body }, { status: 201 })
  }),

  http.patch('/api/schedules/:id', async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ id: Number(params.id), period_start: '2026-05-01', period_end: '2026-05-31', situation: '수정됨', ...body })
  }),

  http.delete('/api/schedules/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get('/api/diary/:date', ({ params }) => {
    const { date } = params
    if (date === '2026-05-01') {
      return HttpResponse.json({ date: '2026-05-01', body: '오늘의 일기 내용입니다.', emotion: 'happy' })
    }
    return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
  }),

  http.patch('/api/diary/:date/emotion', async ({ params, request }) => {
    const { date } = params
    const body = await request.json() as { emotion: string }
    return HttpResponse.json({ date, body: '오늘의 일기 내용입니다.', emotion: body.emotion })
  }),

  http.patch('/api/diary/:date/body', async ({ params, request }) => {
    const { date } = params
    const body = await request.json() as { body: string }
    return HttpResponse.json({ date, body: body.body, emotion: 'happy' })
  }),

  http.get('/api/diary/search', ({ request }) => {
    const q = new URL(request.url).searchParams.get('q') ?? ''
    if (!q) return HttpResponse.json({ results: [] })
    return HttpResponse.json({
      results: [
        { date: '2026-05-15', snippet: `오늘은 ${q}을 했다`, emotion: 'happy' },
      ],
    })
  }),

  http.get('/api/user/streak', () => HttpResponse.json({ streak: 0 })),

  http.get('/api/pet', () => HttpResponse.json({ level: 1, xp: 0, xp_to_next: 100 })),

  http.post('/api/diary/:date/share', () =>
    HttpResponse.json({ token: 'test-token', url: '/share/test-token', expires_at: '2099-01-01T00:00:00Z' })
  ),
]
