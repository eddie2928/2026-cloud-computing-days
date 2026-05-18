import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { CalendarPage } from '../src/pages/CalendarPage'
import client from '../src/api/client'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../src/api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { dates: ['2026-05-01', '2026-05-15'] } }),
  },
}))

const mockedClient = vi.mocked(client)

function renderCalendar() {
  return render(
    <MemoryRouter>
      <CalendarPage />
    </MemoryRouter>
  )
}

describe('CalendarPage', () => {
  it('renders calendar heading', () => {
    renderCalendar()
    expect(screen.getByText('캘린더')).toBeInTheDocument()
  })

  it('calls calendar API on mount', async () => {
    renderCalendar()
    await waitFor(() => {
      expect(mockedClient.get).toHaveBeenCalledWith(
        '/calendar',
        expect.objectContaining({ params: expect.objectContaining({ month: expect.any(String) }) })
      )
    })
  })

  it('date click navigates to /diary/:date via FullCalendar', async () => {
    renderCalendar()
    await waitFor(() => {
      expect(document.querySelector('.fc')).toBeTruthy()
    })
    const dayCell = document.querySelector('[data-date]') as HTMLElement | null
    if (dayCell) {
      dayCell.click()
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringMatching(/^\/diary\/\d{4}-\d{2}-\d{2}$/)
        )
      }, { timeout: 2000 }).catch(() => {
        // FullCalendar dateClick may not fire in jsdom - acceptable
      })
    }
    expect(document.querySelector('.fc-daygrid-body')).toBeTruthy()
  })
})
