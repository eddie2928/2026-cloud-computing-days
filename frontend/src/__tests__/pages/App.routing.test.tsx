/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'

// Mock BrowserRouter → MemoryRouter with /profile/taste as initial entry
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  const { MemoryRouter } = actual
  return {
    ...actual,
    BrowserRouter: ({ children }: { children: ReactNode }) => (
      <MemoryRouter initialEntries={['/profile/taste']}>{children}</MemoryRouter>
    ),
  }
})

// Mock useAuth to return authenticated state
vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    isAuthed: true,
    checkAuth: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

// Mock api/client: GET /profile → success, GET /me → success
vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { id: 1, name: 'testuser' } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}))

// Mock api/taste to avoid real HTTP calls
vi.mock('../../api/taste', () => ({
  getTasteProfile: vi.fn().mockRejectedValue({ response: { status: 404 } }),
  putTasteProfile: vi.fn().mockResolvedValue({}),
}))

// Mock lib/push to avoid navigator.serviceWorker access
vi.mock('../../lib/push', () => ({
  getPushState: vi.fn().mockResolvedValue('not-subscribed'),
  subscribePush: vi.fn(),
}))

// Mock lib/mockDate (must include MOCK_DATE_EVENT used by useMockDate hook)
vi.mock('../../lib/mockDate', () => ({
  getMockDate: vi.fn().mockReturnValue(''),
  setMockDate: vi.fn(),
  clearMockDate: vi.fn(),
  hasMockDate: vi.fn().mockReturnValue(false),
  MOCK_DATE_EVENT: 'days-mock-date-changed',
}))

// Mock lib/season to avoid DOM side effects
vi.mock('../../lib/season', () => ({
  applySeason: vi.fn(),
}))

import App from '../../App'

describe('App 라우팅 스모크', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('/profile/taste 라우트가 TasteSurvey를 렌더링한다', async () => {
    render(<App />)
    // TasteSurvey 1단계 진입 확인 (404 mock이므로 빈 폼으로 시작)
    await waitFor(
      () => expect(screen.getByText('1 / 11단계')).toBeInTheDocument(),
      { timeout: 3000 },
    )
    expect(screen.getByText('좋아하는 음악 장르를 선택해주세요')).toBeInTheDocument()
  })
})
