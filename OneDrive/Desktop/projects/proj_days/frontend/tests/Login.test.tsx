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
  it('correct password navigates to /qna', async () => {
    renderLogin()
    await userEvent.type(screen.getByLabelText('비밀번호'), 'inha-nxt')
    await userEvent.click(screen.getByRole('button', { name: '로그인' }))
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/qna'))
  })

  it('wrong password shows error message', async () => {
    renderLogin()
    await userEvent.type(screen.getByLabelText('비밀번호'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: '로그인' }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('empty input keeps submit button disabled', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: '로그인' })).toBeDisabled()
  })
})
