import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { ChatSessionModal } from '../src/components/ChatSessionModal'
import { server } from './setup'

function renderModal(date: string | null = '2026-05-20') {
  const onClose = vi.fn()
  const onComplete = vi.fn()
  render(<ChatSessionModal date={date} onClose={onClose} onComplete={onComplete} />)
  return { onClose, onComplete }
}

describe('ChatSessionModal', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.runAllTimers()
    vi.useRealTimers()
  })

  it('progress=0 상태에서 닫기 클릭 시 토스트 없이 onClose 즉시 호출', async () => {
    const { onClose } = renderModal()
    await waitFor(() => expect(screen.getByText(/오늘 가장 기억에 남는/)).toBeInTheDocument())

    const closeBtn = screen.getByRole('button', { name: '닫기' })
    await userEvent.click(closeBtn)

    expect(onClose).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/진행 상황은 저장됐어요/)).not.toBeInTheDocument()
  })

  it('progress>=1 상태에서 닫기 클릭 시 토스트 1.5초 후 onClose 호출', async () => {
    const { onClose } = renderModal()
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await userEvent.type(screen.getByRole('textbox'), '첫 번째 답변')
    await userEvent.click(screen.getByRole('button', { name: '전송' }))
    await waitFor(() => expect(screen.getByText(/다음 질문 2번/)).toBeInTheDocument())

    const closeBtn = screen.getByRole('button', { name: '닫기' })
    await userEvent.click(closeBtn)

    expect(screen.getByText(/진행 상황은 저장됐어요/)).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()

    act(() => { vi.advanceTimersByTime(1600) })

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('finalizing 중 닫기 클릭 시 onClose 미호출 + 안내 문구 표시', async () => {
    server.use(
      http.post('/api/qna/start', () =>
        HttpResponse.json({
          session_id: 1,
          question: '다섯 번째 질문입니다.',
          sequence: 5,
          history: [],
        })
      ),
      http.post('/api/qna/answer', () =>
        new Promise((resolve) =>
          setTimeout(
            () => resolve(HttpResponse.json({ completed: true, diary: '일기 내용' })),
            5000
          )
        )
      )
    )
    const { onClose } = renderModal()
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await userEvent.type(screen.getByRole('textbox'), '다섯 번째 답변')
    await userEvent.click(screen.getByRole('button', { name: '전송' }))

    await waitFor(() => expect(screen.getByText(/당신의 일기를 만들고 있어요/)).toBeInTheDocument())

    const closeBtn = screen.getByRole('button', { name: '닫기' })
    await userEvent.click(closeBtn)

    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByText(/거의 다 됐어요/)).toBeInTheDocument()
  })
})
