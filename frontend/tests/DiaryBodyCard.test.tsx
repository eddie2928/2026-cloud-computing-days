import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { DiaryBodyCard } from '../src/components/diary/DiaryBodyCard'

describe('DiaryBodyCard', () => {
  it('편집 버튼 클릭 → textarea 표시', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<DiaryBodyCard body="기존 본문" onSave={onSave} />)
    await userEvent.click(screen.getByRole('button', { name: '편집' }))
    expect(screen.getByLabelText('일기 본문 편집')).toBeInTheDocument()
  })

  it('저장 → onSave 호출 후 편집 모드 종료', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<DiaryBodyCard body="기존 본문" onSave={onSave} />)
    await userEvent.click(screen.getByRole('button', { name: '편집' }))
    const textarea = screen.getByLabelText('일기 본문 편집') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: '수정된 본문' } })
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith('수정된 본문')
    })
    expect(screen.queryByLabelText('일기 본문 편집')).toBeNull()
  })

  it('5001자 입력 → 5000자로 잘림', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<DiaryBodyCard body="" onSave={onSave} />)
    await userEvent.click(screen.getByRole('button', { name: '편집' }))
    const textarea = screen.getByLabelText('일기 본문 편집') as HTMLTextAreaElement
    const longText = 'a'.repeat(5001)
    fireEvent.change(textarea, { target: { value: longText } })
    expect(textarea.value.length).toBe(5000)
  })
})
