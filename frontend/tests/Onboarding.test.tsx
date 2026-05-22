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
  it('GET /profile 404 → Step 1 폼 표시', async () => {
    renderOnboarding()
    await waitFor(() => {
      expect(screen.getByText('기본 정보를 알려주세요')).toBeInTheDocument()
    })
  })

  it('GET /profile 200 → /hub으로 이동', async () => {
    server.use(
      http.get('/api/profile', () =>
        HttpResponse.json({ nickname: '홍길동', gender: 'male', age: 30, hobbies: [], interests: [] })
      )
    )
    renderOnboarding()
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/hub', { replace: true })
    })
  })

  it('3 스텝 완주 후 PUT /profile 호출 → navigate("/hub")', async () => {
    renderOnboarding()
    await waitFor(() => {
      expect(screen.getByText('기본 정보를 알려주세요')).toBeInTheDocument()
    })

    // Step 1
    await userEvent.type(screen.getByLabelText('닉네임'), '테스트유저')
    await userEvent.click(screen.getByRole('button', { name: '남성' }))
    await userEvent.type(screen.getByLabelText('나이'), '25')
    await userEvent.click(screen.getByRole('button', { name: '다음' }))

    // Step 2
    await waitFor(() => expect(screen.getByText('어떤 일을 하세요?')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '다음' }))

    // Step 3
    await waitFor(() => expect(screen.getByText('관심사와 알림 시간')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '시작하기' }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/hub')
    })
  })
})
