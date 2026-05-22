import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
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
