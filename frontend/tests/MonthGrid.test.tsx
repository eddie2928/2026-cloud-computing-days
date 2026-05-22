import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MonthGrid } from '../src/components/calendar/MonthGrid'

const noop = vi.fn()

describe('MonthGrid', () => {
  it('2026-05 → 42개 셀 렌더 (7×6)', () => {
    render(
      <MonthGrid
        year={2026} month={5}
        entries={[]}
        onPrev={noop} onNext={noop} onCellClick={noop}
      />
    )
    const grid = screen.getByTestId('month-grid')
    expect(grid.children).toHaveLength(42)
  })

  it('일요일 시작 — 첫 셀이 일요일(일)', () => {
    render(
      <MonthGrid
        year={2026} month={5}
        entries={[]}
        onPrev={noop} onNext={noop} onCellClick={noop}
      />
    )
    // 2026-05-01은 금요일(5). 첫 셀은 4/26(일요일).
    const cells = screen.getAllByRole('button', { name: /2026-04-26/ })
    expect(cells).toHaveLength(1)
  })

  it('이전/다음 달 네비 버튼 존재', () => {
    render(
      <MonthGrid
        year={2026} month={5}
        entries={[]}
        onPrev={noop} onNext={noop} onCellClick={noop}
      />
    )
    expect(screen.getByLabelText('이전 달')).toBeInTheDocument()
    expect(screen.getByLabelText('다음 달')).toBeInTheDocument()
  })
})
