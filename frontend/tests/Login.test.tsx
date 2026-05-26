import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Login } from '../src/pages/Login'
import { server } from './setup'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockPromptInstall = vi.fn()
const mockInstallState = {
  canInstall: false,
  isIOS: false,
  isIOSSafari: false,
  isStandalone: false,
  promptInstall: mockPromptInstall,
}
vi.mock('../src/hooks/useInstallPrompt', () => ({
  useInstallPrompt: vi.fn(() => ({ ...mockInstallState })),
}))
import { useInstallPrompt } from '../src/hooks/useInstallPrompt'
const mockedHook = vi.mocked(useInstallPrompt)

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  )
}

describe('Login page', () => {
  beforeEach(() => {
    mockedHook.mockReturnValue({ ...mockInstallState })
    mockPromptInstall.mockReset()
  })

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

  it('기본 미설치 환경: "앱으로 설치하기" 버튼 존재', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: /앱으로 설치하기/ })).toBeInTheDocument()
  })

  it('canInstall=false 버튼 클릭 → 안내 모달 열림', async () => {
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: /앱으로 설치하기/ }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('isStandalone=true: 설치 버튼 미존재', () => {
    mockedHook.mockReturnValue({ ...mockInstallState, isStandalone: true })
    renderLogin()
    expect(screen.queryByRole('button', { name: /앱으로 설치하기/ })).not.toBeInTheDocument()
  })

  it('canInstall=true 버튼 클릭 → promptInstall 호출 (모달 미열림)', async () => {
    mockPromptInstall.mockResolvedValue(true)
    mockedHook.mockReturnValue({ ...mockInstallState, canInstall: true })
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: /앱으로 설치하기/ }))
    expect(mockPromptInstall).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('canInstall=true이나 설치 프롬프트 실패 → 안내 모달 fallback', async () => {
    mockPromptInstall.mockResolvedValue(false)
    mockedHook.mockReturnValue({ ...mockInstallState, canInstall: true })
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: /앱으로 설치하기/ }))
    expect(mockPromptInstall).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument())
  })
})
