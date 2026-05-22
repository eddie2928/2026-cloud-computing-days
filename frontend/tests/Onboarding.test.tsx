import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi } from 'vitest'
import { Onboarding } from '../src/pages/Onboarding'
import { server } from './setup'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderOnboarding() {
  return render(
    <MemoryRouter>
      <Onboarding />
    </MemoryRouter>
  )
}

describe('Onboarding page', () => {
  it('GET /profile 404 응답 시 폼이 표시된다', async () => {
    renderOnboarding()
    await waitFor(() => {
      expect(screen.getByLabelText('닉네임 *')).toBeInTheDocument()
    })
  })

  it('GET /profile 200이면 홈(/)으로 이동한다', async () => {
    server.use(
      http.get('/api/profile', () =>
        HttpResponse.json({ nickname: '홍길동', gender: 'male', age: 30, hobbies: [], interests: [] })
      )
    )
    renderOnboarding()
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })

  it('필수 항목 입력 후 제출 시 PUT /profile 호출 + navigate("/")', async () => {
    renderOnboarding()
    await waitFor(() => {
      expect(screen.getByLabelText('닉네임 *')).toBeInTheDocument()
    })
    await userEvent.type(screen.getByLabelText('닉네임 *'), '테스트')
    await userEvent.click(screen.getByLabelText('남'))
    await userEvent.clear(screen.getByLabelText('나이 *'))
    await userEvent.type(screen.getByLabelText('나이 *'), '25')
    await userEvent.click(screen.getByRole('button', { name: '시작하기' }))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })
})
