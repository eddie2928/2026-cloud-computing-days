import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { DayModal } from '../src/components/calendar/DayModal'

function renderModal(date: string) {
  return render(
    <MemoryRouter>
      <DayModal date={date} onClose={() => {}} />
    </MemoryRouter>
  )
}

describe('DayModal', () => {
  it('200 응답 시 일기 본문 렌더', async () => {
    renderModal('2026-05-01')
    await waitFor(() => {
      expect(screen.getByText('오늘의 일기 내용입니다.')).toBeInTheDocument()
    })
  })

  it('404 응답 시 QnA 채팅 모달 렌더', async () => {
    renderModal('2026-05-22')
    await waitFor(() => {
      expect(screen.getByText('오늘 가장 기억에 남는 일은 무엇인가요?')).toBeInTheDocument()
    })
  })
})
