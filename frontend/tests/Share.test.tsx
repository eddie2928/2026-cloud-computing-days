import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { Share } from '../src/pages/Share'
import { server } from './setup'

function renderShare(token: string) {
  return render(
    <MemoryRouter initialEntries={[`/share/${token}`]}>
      <Routes>
        <Route path="/share/:token" element={<Share />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('Share page', () => {
  it('유효 토큰 → 일기 본문 렌더', async () => {
    server.use(
      http.get('/api/share/:token', () =>
        HttpResponse.json({ date: '2026-05-01', body: '공유된 일기 내용', emotion: 'happy' })
      )
    )
    renderShare('valid-token')
    await waitFor(() => {
      expect(screen.getByText('공유된 일기 내용')).toBeInTheDocument()
    })
  })

  it('만료 토큰 → 만료 안내 렌더', async () => {
    server.use(
      http.get('/api/share/:token', () =>
        HttpResponse.json({ detail: 'Share link expired' }, { status: 410 })
      )
    )
    renderShare('expired-token')
    await waitFor(() => {
      expect(screen.getByText('링크가 만료되었어요.')).toBeInTheDocument()
    })
  })
})
