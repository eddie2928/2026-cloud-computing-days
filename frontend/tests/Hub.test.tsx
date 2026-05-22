import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { Hub } from '../src/pages/Hub'
import { server } from './setup'

function renderHub() {
  return render(
    <MemoryRouter>
      <Hub />
    </MemoryRouter>
  )
}

describe('Hub page', () => {
  it('calendar 응답 후 WeekStrip 7셀 렌더', async () => {
    renderHub()
    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      // WeekStrip 7 + Logo + 검색 버튼 포함, 최소 7개 이상
      expect(buttons.length).toBeGreaterThanOrEqual(7)
    })
  })

  it('오늘 diary 없을 때 "오늘의 일기 시작" 버튼 표시', async () => {
    server.use(
      http.get('/api/diary/:date', () => HttpResponse.json({ detail: 'Not found' }, { status: 404 }))
    )
    renderHub()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '오늘의 일기 시작' })).toBeInTheDocument()
    })
  })
})
