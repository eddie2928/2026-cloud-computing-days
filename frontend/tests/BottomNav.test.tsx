import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { BottomNav } from '../src/components/layout/BottomNav'
import { getMockDate } from '../src/lib/mockDate'
import { server } from './setup'

function renderNav(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <BottomNav />
    </MemoryRouter>
  )
}

function LocationProbe() {
  const loc = useLocation()
  return <div data-testid="loc">{loc.pathname}</div>
}

function renderNavWithProbe(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <BottomNav />
      <Routes>
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('BottomNav', () => {
  it('/hub 진입 시 홈 슬롯에 aria-current=page', () => {
    renderNav('/hub')
    const hubBtn = screen.getByRole('button', { name: /홈/ })
    expect(hubBtn).toHaveAttribute('aria-current', 'page')
  })

  it('/calendar 진입 시 캘린더 슬롯에 aria-current=page', () => {
    renderNav('/calendar')
    const calBtn = screen.getByRole('button', { name: /캘린더/ })
    expect(calBtn).toHaveAttribute('aria-current', 'page')
  })

  it('/login 진입 시 아무 슬롯도 active 아님', () => {
    renderNav('/login')
    const buttons = screen.getAllByRole('button')
    buttons.forEach(btn => {
      expect(btn).not.toHaveAttribute('aria-current', 'page')
    })
  })

  it('오늘 일기가 있으면 오늘의 일기 버튼 → /diary/{today}', async () => {
    const today = getMockDate()
    server.use(
      http.get('/api/calendar', () =>
        HttpResponse.json({ entries: [{ date: today }], schedules: [], holidays: [] })
      )
    )
    renderNavWithProbe('/hub')
    await userEvent.click(screen.getByRole('button', { name: /오늘의 일기/ }))
    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe(`/diary/${today}`)
    })
  })

  it('오늘 일기가 없으면 오늘의 일기 버튼 → /qna/{today}', async () => {
    const today = getMockDate()
    server.use(
      http.get('/api/calendar', () =>
        HttpResponse.json({ entries: [], schedules: [], holidays: [] })
      )
    )
    renderNavWithProbe('/hub')
    await userEvent.click(screen.getByRole('button', { name: /오늘의 일기/ }))
    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe(`/qna/${today}`)
    })
  })

  it('calendar API 실패 시 오늘의 일기 버튼 → /qna/{today}', async () => {
    const today = getMockDate()
    server.use(
      http.get('/api/calendar', () =>
        HttpResponse.json({ detail: 'oops' }, { status: 500 })
      )
    )
    renderNavWithProbe('/hub')
    await userEvent.click(screen.getByRole('button', { name: /오늘의 일기/ }))
    await waitFor(() => {
      expect(screen.getByTestId('loc').textContent).toBe(`/qna/${today}`)
    })
  })
})
