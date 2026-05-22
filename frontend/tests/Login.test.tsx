import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi } from 'vitest'
import { Login } from '../src/pages/Login'
import { server } from './setup'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  )
}

describe('Login page', () => {
  it('로그인 성공 + GET /profile 404 → /onboarding으로 이동', async () => {
    renderLogin()
    await userEvent.type(screen.getByLabelText('비밀번호'), 'inha-nxt')
    await userEvent.click(screen.getByRole('button', { name: /시작하기/ }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/onboarding'))
  })

  it('로그인 성공 + GET /profile 200 → /hub으로 이동', async () => {
    server.use(
      http.get('/api/profile', () =>
        HttpResponse.json({ nickname: '홍길동', gender: 'male', age: 30, hobbies: [], interests: [] })
      )
    )
    renderLogin()
    await userEvent.type(screen.getByLabelText('비밀번호'), 'inha-nxt')
    await userEvent.click(screen.getByRole('button', { name: /시작하기/ }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/hub'))
  })

  it('wrong password shows error message', async () => {
    renderLogin()
    await userEvent.type(screen.getByLabelText('비밀번호'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /시작하기/ }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('empty input keeps submit button disabled', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /시작하기/ })).toBeDisabled()
  })
})
