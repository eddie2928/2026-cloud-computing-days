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
  it('마운트 시 GET /profile → 닉네임 표시', async () => {
    renderProfile()
    await waitFor(() => {
      expect(screen.getAllByText('홍길동').length).toBeGreaterThan(0)
    })
  })

  it('기본정보 수정 → 저장 → PUT /profile 호출 + 갱신 표시', async () => {
    let capturedBody: unknown = null
    server.use(
      http.put('/api/profile', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(capturedBody)
      })
    )
    renderProfile()
    await waitFor(() => expect(screen.getAllByText('홍길동').length).toBeGreaterThan(0))
    await userEvent.click(screen.getAllByRole('button', { name: '수정' })[0])
    const nicknameInput = screen.getByLabelText('닉네임 수정')
    await userEvent.clear(nicknameInput)
    await userEvent.type(nicknameInput, '새이름')
    await userEvent.click(screen.getAllByRole('button', { name: '저장' })[0])
    await waitFor(() => {
      expect(capturedBody).toBeTruthy()
    })
    expect((capturedBody as { nickname: string }).nickname).toBe('새이름')
  })

  it('알림 시간 섹션 미표시 + PUT 페이로드에 notification_time 키 없음', async () => {
    let capturedBody: Record<string, unknown> = {}
    server.use(
      http.put('/api/profile', async ({ request }) => {
        capturedBody = await request.json() as Record<string, unknown>
        return HttpResponse.json(capturedBody)
      })
    )
    renderProfile()
    await waitFor(() => expect(screen.getAllByText('홍길동').length).toBeGreaterThan(0))
    expect(screen.queryByLabelText('알림 시간 수정')).toBeNull()

    await userEvent.click(screen.getAllByRole('button', { name: '수정' })[0])
    await userEvent.click(screen.getAllByRole('button', { name: '저장' })[0])
    await waitFor(() => expect(capturedBody).not.toEqual({}))
    expect(capturedBody).not.toHaveProperty('notification_time')
  })

  it('로그아웃 버튼 클릭 시 navigate("/login")', async () => {
    renderProfile()
    await waitFor(() => expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }))
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })
})
