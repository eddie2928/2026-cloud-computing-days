import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { GlobalHeader } from '../src/components/layout/GlobalHeader'

describe('GlobalHeader', () => {
  it('헤더가 로고와 개발자 버튼을 렌더한다', () => {
    render(
      <MemoryRouter>
        <GlobalHeader />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: '홈으로' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '개발자' })).toBeInTheDocument()
  })

  it('헤더 버튼 aria-label 노출', () => {
    render(
      <MemoryRouter>
        <GlobalHeader />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: '개발자' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '홈으로' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '개발자' }))
  })
})
