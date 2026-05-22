import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { Qna } from '../src/pages/QnA'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

function renderQna(date: string) {
  return render(
    <MemoryRouter initialEntries={[`/qna/${date}`]}>
      <Routes>
        <Route path="/qna/:date" element={<Qna />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('Qna page', () => {
  it('ChatBubble role별 정렬 — ai는 왼쪽', async () => {
    renderQna('2026-05-22')
    await waitFor(() => {
      expect(screen.getByText('오늘 가장 기억에 남는 일은 무엇인가요?')).toBeInTheDocument()
    })
  })

  it('start → answer 1회 → 진척도 1/5→2/5', async () => {
    renderQna('2026-05-22')
    await waitFor(() => {
      expect(screen.getByText(/1\s*\/\s*5/)).toBeInTheDocument()
    })
    const input = screen.getByLabelText('답변 입력')
    await userEvent.type(input, '오늘은 좋은 일이 있었어요')
    await userEvent.click(screen.getByLabelText('전송'))
    await waitFor(() => {
      expect(screen.getByText(/2\s*\/\s*5/)).toBeInTheDocument()
    })
  })
})
