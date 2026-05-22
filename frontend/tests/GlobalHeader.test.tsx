import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { GlobalHeader } from '../src/components/layout/GlobalHeader'
import { server } from './setup'

describe('GlobalHeader', () => {
  it('프로필 응답 후 닉네임 텍스트 렌더', async () => {
    server.use(
      http.get('/api/profile', () =>
        HttpResponse.json({ nickname: '지민', gender: 'female', age: 25 })
      )
    )
    render(
      <MemoryRouter>
        <GlobalHeader />
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByText('지민')).toBeInTheDocument()
    })
  })

  it('프로필 버튼 클릭 시 aria-label 노출', () => {
    render(
      <MemoryRouter>
        <GlobalHeader />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: '프로필' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '홈으로' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '프로필' }))
  })
})
