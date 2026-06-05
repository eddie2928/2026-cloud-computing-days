/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Admin } from '../../pages/Admin'
import * as plantTest from '../../lib/plantTest'

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}))
vi.mock('../../lib/push', () => ({
  getPushState: vi.fn().mockResolvedValue('not-subscribed'),
  subscribePush: vi.fn(),
}))
vi.mock('../../lib/mockDate', () => ({
  getMockDate: vi.fn().mockReturnValue(''),
  setMockDate: vi.fn(),
  clearMockDate: vi.fn(),
  hasMockDate: vi.fn().mockReturnValue(false),
}))
vi.mock('../../api/music', () => ({
  searchMusic: vi.fn().mockResolvedValue({ ok: true, status_code: 200, latency_ms: 0, results: [] }),
}))

beforeEach(() => {
  localStorage.clear()
  vi.spyOn(plantTest, 'setPlantTestSeason')
  vi.spyOn(plantTest, 'setPlantTestState')
  vi.spyOn(plantTest, 'clearPlantTest')
})

function renderAdmin() {
  return render(<MemoryRouter><Admin /></MemoryRouter>)
}

describe('Admin pet tab', () => {
  it('renders pet tab button', () => {
    renderAdmin()
    expect(screen.getByRole('button', { name: /펫/ })).toBeInTheDocument()
  })

  it('shows season and state selects after clicking pet tab', () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /펫/ }))
    const combos = screen.getAllByRole('combobox')
    // season select has spring/summer options, state select has 시듦/보통/무럭무럭
    expect(combos.some(el => el.textContent?.includes('봄'))).toBe(true)
    expect(combos.some(el => el.textContent?.includes('시듦'))).toBe(true)
  })

  it('calls setPlantTestSeason and setPlantTestState on 적용', () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /펫/ }))
    fireEvent.click(screen.getByRole('button', { name: '적용' }))
    expect(plantTest.setPlantTestSeason).toHaveBeenCalled()
    expect(plantTest.setPlantTestState).toHaveBeenCalled()
  })

  it('calls clearPlantTest on 초기화', () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: /펫/ }))
    fireEvent.click(screen.getByRole('button', { name: '초기화' }))
    expect(plantTest.clearPlantTest).toHaveBeenCalled()
  })
})
