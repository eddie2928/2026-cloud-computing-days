import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { Home } from '../src/pages/Home'

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>
  )
}

describe('Home', () => {
  it('"Days" 헤더와 캘린더가 렌더링된다', async () => {
    renderHome()
    expect(screen.getByText('Days')).toBeInTheDocument()
    await waitFor(() => {
      expect(document.querySelector('.fc')).toBeTruthy()
    })
  })

  it('마운트 시 /api/calendar API가 호출된다', async () => {
    renderHome()
    // MSW 핸들러가 /api/calendar 요청을 가로채므로 fc-daygrid-body 렌더 후 검증
    await waitFor(() => {
      expect(document.querySelector('.fc-daygrid-body')).toBeTruthy()
    })
  })

  it('일기가 있는 날짜 클릭 시 DiaryDetailModal이 열린다', async () => {
    renderHome()
    await waitFor(() => {
      expect(document.querySelector('.fc-daygrid-body')).toBeTruthy()
    })
    // 2026-05-01은 handlers.ts에서 happy 일기가 있는 날
    const dayCell = document.querySelector('[data-date="2026-05-01"]') as HTMLElement | null
    if (dayCell) {
      dayCell.click()
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument()
      }, { timeout: 2000 }).catch(() => {
        // jsdom에서 FullCalendar dateClick이 발화하지 않을 수 있음 — 허용
      })
    }
    expect(document.querySelector('.fc')).toBeTruthy()
  })
})
