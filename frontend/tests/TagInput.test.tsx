import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useState } from 'react'
import { TagInput } from '../src/components/days/TagInput'

function Harness({ initial = [] as string[], onChange }: { initial?: string[]; onChange?: (v: string[]) => void }) {
  const [tags, setTags] = useState<string[]>(initial)
  return (
    <TagInput
      value={tags}
      onChange={(v) => {
        setTags(v)
        onChange?.(v)
      }}
      placeholder="예: 독서"
      ariaLabel="태그 입력"
    />
  )
}

describe('TagInput', () => {
  it('저장 버튼 클릭으로 태그 추가', () => {
    const handleChange = vi.fn()
    render(<Harness onChange={handleChange} />)
    const input = screen.getByLabelText('태그 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '독서' } })
    fireEvent.click(screen.getByRole('button', { name: '태그 저장' }))
    expect(handleChange).toHaveBeenCalledWith(['독서'])
    expect(screen.getByText('독서')).toBeInTheDocument()
  })

  it('Enter 키로도 태그 추가', () => {
    const handleChange = vi.fn()
    render(<Harness onChange={handleChange} />)
    const input = screen.getByLabelText('태그 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '운동' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(handleChange).toHaveBeenCalledWith(['운동'])
    expect(screen.getByText('운동')).toBeInTheDocument()
  })

  it('쉼표 입력만으로는 태그가 추가되지 않음', () => {
    const handleChange = vi.fn()
    render(<Harness onChange={handleChange} />)
    const input = screen.getByLabelText('태그 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '운동,' } })
    expect(handleChange).not.toHaveBeenCalled()
    expect(screen.queryByText('운동')).not.toBeInTheDocument()
  })

  it('빈 입력일 때 저장 버튼은 비활성화', () => {
    render(<Harness />)
    const saveBtn = screen.getByRole('button', { name: '태그 저장' }) as HTMLButtonElement
    expect(saveBtn.disabled).toBe(true)
  })

  it('태그 ✕ 버튼 클릭으로 삭제', () => {
    const handleChange = vi.fn()
    render(<Harness initial={['독서', '운동']} onChange={handleChange} />)
    const removeBtn = screen.getByRole('button', { name: '독서 삭제' })
    fireEvent.click(removeBtn)
    expect(handleChange).toHaveBeenCalledWith(['운동'])
  })

  it('중복 태그는 무시', () => {
    const handleChange = vi.fn()
    render(<Harness initial={['독서']} onChange={handleChange} />)
    const input = screen.getByLabelText('태그 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '독서' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(handleChange).not.toHaveBeenCalled()
  })
})
