import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { WeekStrip } from '../src/components/hub/WeekStrip'
import { getWeekWindow } from '../src/lib/week'

const TODAY = '2026-05-22'
const DAYS = getWeekWindow(
  [{ date: TODAY, emotion: 'happy' }],
  TODAY
)

function renderStrip() {
  return render(
    <MemoryRouter>
      <WeekStrip days={DAYS} today={TODAY} />
    </MemoryRouter>
  )
}

describe('WeekStrip', () => {
  it('7개 셀 렌더', () => {
    renderStrip()
    expect(screen.getAllByRole('button')).toHaveLength(7)
  })

  it('오늘 셀에 aria-current=date', () => {
    renderStrip()
    const todayBtn = screen.getByRole('button', { current: 'date' })
    expect(todayBtn).toBeInTheDocument()
  })
})
