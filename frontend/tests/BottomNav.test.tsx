import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { BottomNav } from '../src/components/layout/BottomNav'

function renderNav(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <BottomNav />
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
})
