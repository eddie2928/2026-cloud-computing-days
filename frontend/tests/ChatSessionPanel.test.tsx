import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import { ChatSessionPanel } from '../src/components/ChatSessionPanel'
import { server } from './setup'

const noop = () => {}

function renderPanel(date = '2026-05-11') {
  const onComplete = vi.fn()
  render(<ChatSessionPanel date={date} onComplete={onComplete} onClose={noop} />)
  return { onComplete }
}

describe('ChatSessionPanel', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('마운트 시 첫 번째 질문을 표시한다', async () => {
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/오늘 가장 기억에 남는/)).toBeInTheDocument()
    })
  })

  it('5회 답변 후 onComplete가 일기 문자열로 호출된다', async () => {
    const { onComplete } = renderPanel('2026-05-11')
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    for (let i = 1; i <= 5; i++) {
      await userEvent.type(screen.getByRole('textbox'), `답변 ${i}`)
      await userEvent.click(screen.getByRole('button', { name: '전송' }))
      if (i < 5) {
        await waitFor(() => expect(screen.getByText(new RegExp(`다음 질문 ${i + 1}번`))).toBeInTheDocument())
      }
    }

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('오늘 하루를 돌아보며 작성된 일기입니다.')
    })
  })

  it('409 응답 시 입력창 비활성 + 안내 메시지', async () => {
    server.use(
      http.post('/api/qna/start', () =>
        HttpResponse.json({ detail: 'Diary already completed for this date' }, { status: 409 })
      )
    )
    renderPanel('2026-05-01')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('이미 완료된 날짜입니다.')
    })
  })

  it('history 응답 시 이전 Q/A가 화면에 복원되고 마지막 미답변 질문이 표시된다', async () => {
    server.use(
      http.post('/api/qna/start', () =>
        HttpResponse.json({
          session_id: 1,
          question: '세 번째 질문입니다.',
          sequence: 3,
          history: [
            { sequence: 1, question: '첫 번째 질문이에요.', answer: '첫 번째 답변이에요.' },
            { sequence: 2, question: '두 번째 질문이에요.', answer: '두 번째 답변이에요.' },
          ],
        })
      )
    )
    renderPanel('2026-05-12')
    await waitFor(() => {
      expect(screen.getByText('첫 번째 질문이에요.')).toBeInTheDocument()
      expect(screen.getByText('첫 번째 답변이에요.')).toBeInTheDocument()
      expect(screen.getByText('두 번째 질문이에요.')).toBeInTheDocument()
      expect(screen.getByText('두 번째 답변이에요.')).toBeInTheDocument()
      expect(screen.getByText('세 번째 질문입니다.')).toBeInTheDocument()
    })
  })

  it('5번째 답변 전송 시 finalizing 로딩 UI가 표시된다', async () => {
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
          setTimeout(() => resolve(HttpResponse.json({ completed: true, diary: '일기 내용' })), 100)
        )
      )
    )
    const { onComplete } = renderPanel('2026-05-13')
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await userEvent.type(screen.getByRole('textbox'), '다섯 번째 답변')
    await userEvent.click(screen.getByRole('button', { name: '전송' }))

    await waitFor(() => {
      expect(screen.getByText(/당신의 일기를 만들고 있어요/)).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith('일기 내용')
    })
  })
})
