import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { Calendar } from '../src/pages/Calendar'
import { server } from './setup'

function renderCalendar() {
  return render(
    <MemoryRouter>
      <Calendar />
    </MemoryRouter>
  )
}

describe('Calendar page', () => {
  it('마운트 시 현재 월 그리드 렌더', async () => {
    renderCalendar()
    await waitFor(() => {
      expect(screen.getByTestId('month-grid')).toBeInTheDocument()
    })
  })

  it('다음 달 버튼 클릭 → 새 month 쿼리 호출', async () => {
    const queriedMonths: string[] = []
    server.use(
      http.get('/api/calendar', ({ request }) => {
        const url = new URL(request.url)
        const m = url.searchParams.get('month')
        if (m) queriedMonths.push(m)
        return HttpResponse.json({ entries: [] })
      })
    )
    renderCalendar()
    await waitFor(() => expect(screen.getByTestId('month-grid')).toBeInTheDocument())
    const initialCount = queriedMonths.length
    await userEvent.click(screen.getByLabelText('다음 달'))
    await waitFor(() => {
      expect(queriedMonths.length).toBeGreaterThan(initialCount)
    })
  })
})
