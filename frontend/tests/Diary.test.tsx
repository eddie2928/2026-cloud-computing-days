import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi } from 'vitest'
import { Diary } from '../src/pages/Diary'
import { server } from './setup'

function renderDiary(date: string) {
  return render(
    <MemoryRouter initialEntries={[`/diary/${date}`]}>
      <Routes>
        <Route path="/diary/:date" element={<Diary />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('Diary page', () => {
  it('diary 응답 → 본문 + emotion 표시', async () => {
    server.use(
      http.get('/api/diary/:date', () =>
        HttpResponse.json({ date: '2026-05-01', body: '오늘의 일기 내용입니다.', emotion: 'happy' })
      )
    )
    renderDiary('2026-05-01')
    await waitFor(() => {
      expect(screen.getByText('오늘의 일기 내용입니다.')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'happy', pressed: true })).toBeInTheDocument()
  })

  it('"다시 작성하기" 버튼 없음', async () => {
    server.use(
      http.get('/api/diary/:date', () =>
        HttpResponse.json({ date: '2026-05-01', body: '일기', emotion: 'neutral' })
      )
    )
    renderDiary('2026-05-01')
    await waitFor(() => expect(screen.getByText('일기')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: '다시 작성하기' })).toBeNull()
  })

  it('공유 클릭 → clipboard.writeText 호출', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    server.use(
      http.get('/api/diary/:date', () =>
        HttpResponse.json({ date: '2026-05-01', body: '일기', emotion: 'neutral' })
      ),
      http.post('/api/diary/:date/share', () =>
        HttpResponse.json({ token: 'abc123', url: '/share/abc123', expires_at: '2099-01-01T00:00:00Z' })
      )
    )
    renderDiary('2026-05-01')
    await waitFor(() => expect(screen.getByRole('button', { name: '공유' })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '공유' }))
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(expect.stringContaining('/share/abc123'))
    })
  })

  it('편집 → 저장 → PATCH /diary/:date/body 호출', async () => {
    let patchBody: Record<string, unknown> = {}
    server.use(
      http.get('/api/diary/:date', () =>
        HttpResponse.json({ date: '2026-05-01', body: '기존 본문', emotion: 'neutral' })
      ),
      http.patch('/api/diary/:date/body', async ({ request }) => {
        patchBody = await request.json() as Record<string, unknown>
        return HttpResponse.json({ date: '2026-05-01', body: patchBody.body, emotion: 'neutral' })
      })
    )
    renderDiary('2026-05-01')
    await waitFor(() => expect(screen.getByText('기존 본문')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '편집' }))
    const textarea = screen.getByLabelText('일기 본문 편집') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: '수정된 본문' } })
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    await waitFor(() => {
      expect(patchBody).toEqual({ body: '수정된 본문' })
    })
  })

  it('낙관적 업데이트 — PATCH 실패 시 원복', async () => {
    server.use(
      http.get('/api/diary/:date', () =>
        HttpResponse.json({ date: '2026-05-01', body: '일기 내용', emotion: 'neutral' })
      ),
      http.patch('/api/diary/:date/emotion', () =>
        HttpResponse.json({ detail: 'error' }, { status: 422 })
      )
    )
    renderDiary('2026-05-01')
    await waitFor(() => expect(screen.getByRole('button', { name: 'neutral', pressed: true })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'sad' }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'neutral', pressed: true })).toBeInTheDocument()
    })
  })
})
