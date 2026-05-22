import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, it, expect, vi } from 'vitest'
import { DiaryDetailModal } from '../src/components/DiaryDetailModal'
import { server } from './setup'

function renderModal(date = '2026-05-01') {
  return render(
    <DiaryDetailModal date={date} onClose={vi.fn()} onUpdated={vi.fn()} />
  )
}

describe('DiaryDetailModal', () => {
  it('마운트 시 GET diary 호출 후 body와 이모티콘을 표시한다', async () => {
    renderModal()
    await waitFor(() => {
      expect(screen.getByText(/오늘의 일기 내용입니다/)).toBeInTheDocument()
    })
    // happy 이모티콘
    expect(screen.getByText('😊')).toBeInTheDocument()
  })

  it('감정 이모티콘 클릭 시 EmotionPicker가 나타나고 선택 시 PATCH 요청이 전송된다', async () => {
    let patchCalled = false
    server.use(
      http.patch('/api/diary/:date/emotion', async () => {
        patchCalled = true
        return HttpResponse.json({ date: '2026-05-01', body: '오늘의 일기 내용입니다.', emotion: 'sad' })
      })
    )

    renderModal()
    // 일기 로드 대기
    await waitFor(() => {
      expect(screen.getByText('😊')).toBeInTheDocument()
    })

    // 이모티콘 버튼 클릭 → EmotionPicker 열기
    await userEvent.click(screen.getByTitle('감정 변경'))

    // EmotionPicker에서 '슬픔' 선택
    await userEvent.click(screen.getByTitle('슬픔'))

    await waitFor(() => {
      expect(patchCalled).toBe(true)
    })
  })
})
