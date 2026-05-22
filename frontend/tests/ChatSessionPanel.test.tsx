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
})
