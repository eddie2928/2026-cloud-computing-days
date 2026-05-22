import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi } from 'vitest'
import { Profile } from '../src/pages/Profile'
import { server } from './setup'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const PROFILE_DATA = {
  nickname: '홍길동',
  gender: 'male',
  age: 30,
  occupation: '개발자',
  hobbies: ['독서'],
  interests: ['커리어'],
  notification_time: null,
}

function renderProfile() {
  server.use(
    http.get('/api/profile', () => HttpResponse.json(PROFILE_DATA))
  )
  return render(
    <MemoryRouter>
      <Profile />
    </MemoryRouter>
  )
}

describe('Profile page', () => {
  it('마운트 시 GET /profile로 초기값이 폼에 표시된다', async () => {
    renderProfile()
    await waitFor(() => {
      expect((screen.getByLabelText('닉네임 *') as HTMLInputElement).value).toBe('홍길동')
    })
    expect((screen.getByLabelText('나이 *') as HTMLInputElement).value).toBe('30')
  })

  it('닉네임 수정 후 저장 시 PUT /profile 호출 + navigate("/")', async () => {
    let capturedBody: unknown = null
    server.use(
      http.put('/api/profile', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(capturedBody)
      })
    )
    renderProfile()
    await waitFor(() => {
      expect(screen.getByLabelText('닉네임 *')).toBeInTheDocument()
    })
    await userEvent.clear(screen.getByLabelText('닉네임 *'))
    await userEvent.type(screen.getByLabelText('닉네임 *'), '새이름')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
    expect((capturedBody as { nickname: string }).nickname).toBe('새이름')
  })

  it('로그아웃 버튼 클릭 시 POST /logout 호출 + navigate("/login")', async () => {
    renderProfile()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
    })
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })
})
