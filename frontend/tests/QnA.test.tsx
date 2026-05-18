import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, beforeEach } from 'vitest'
import { QnA } from '../src/pages/QnA'
import { server } from './setup'

function renderQnA() {
  return render(
    <MemoryRouter>
      <QnA />
    </MemoryRouter>
  )
}

describe('QnA page', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('date selection then start shows first question', async () => {
    renderQnA()
    await userEvent.type(screen.getByLabelText('날짜 선택'), '2026-05-10')
    await userEvent.click(screen.getByRole('button', { name: '시작' }))
    await waitFor(() => {
      expect(screen.getByText(/오늘 가장 기억에 남는/)).toBeInTheDocument()
    })
  })

  it('5 answer cycle shows diary result', async () => {
    renderQnA()
    await userEvent.type(screen.getByLabelText('날짜 선택'), '2026-05-11')
    await userEvent.click(screen.getByRole('button', { name: '시작' }))

    for (let i = 1; i <= 5; i++) {
      await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())
      await userEvent.type(screen.getByRole('textbox'), `답변 ${i}`)
      await userEvent.click(screen.getByRole('button', { name: '제출' }))
    }

    await waitFor(() => {
      expect(screen.getByText(/일기 생성 완료/)).toBeInTheDocument()
    })
  })

  it('localStorage accumulates answers after each cycle', async () => {
    renderQnA()
    await userEvent.type(screen.getByLabelText('날짜 선택'), '2026-05-12')
    await userEvent.click(screen.getByRole('button', { name: '시작' }))

    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())
    await userEvent.type(screen.getByRole('textbox'), '첫 답변')
    await userEvent.click(screen.getByRole('button', { name: '제출' }))

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem('qna:2026-05-12') || '[]')
      expect(stored.length).toBeGreaterThan(0)
    })
  })

  it('409 completed date shows disabled button with message', async () => {
    server.use(
      http.post('/api/qna/start', () =>
        HttpResponse.json({ detail: 'Diary already completed for this date' }, { status: 409 })
      )
    )
    renderQnA()
    await userEvent.type(screen.getByLabelText('날짜 선택'), '2026-05-01')
    await userEvent.click(screen.getByRole('button', { name: '시작' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '이미 완료됨' })).toBeDisabled()
    })
  })
})
