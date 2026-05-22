import { http, HttpResponse } from 'msw'

export const handlers = [
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
    const body = await request.json() as { diary_date: string }
    return HttpResponse.json({
      session_id: 1,
      question: '오늘 가장 기억에 남는 일은 무엇인가요?',
      sequence: 1,
    })
  }),

  http.post('/api/qna/answer', async ({ request }) => {
    const body = await request.json() as { session_id: number; sequence: number; answer: string }
    if (body.sequence >= 5) {
      return HttpResponse.json({
        completed: true,
        diary: '오늘 하루를 돌아보며 작성된 일기입니다.',
      })
    }
    return HttpResponse.json({
      next_question: `다음 질문 ${body.sequence + 1}번입니다.`,
      sequence: body.sequence + 1,
      completed: false,
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
      })
    }
    return HttpResponse.json({ entries: [] })
  }),

  http.get('/api/diary/:date', ({ params }) => {
    const { date } = params
    if (date === '2026-05-01') {
      return HttpResponse.json({ date: '2026-05-01', body: '오늘의 일기 내용입니다.', emotion: 'happy' })
    }
    return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
  }),
]
