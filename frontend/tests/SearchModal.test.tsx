import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SearchModal } from '../src/components/search/SearchModal'

const ENTRIES = [
  { date: '2026-05-01', emotion: 'happy' },
  { date: '2026-05-15', emotion: 'neutral' },
]

describe('SearchModal', () => {
  it('검색어 입력 시 결과 카드 렌더 + 클릭 시 onSelect 호출', () => {
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(<SearchModal entries={ENTRIES} onClose={onClose} onSelect={onSelect} />)
    const input = screen.getByLabelText('일기 검색 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '05-15' } })
    const result = screen.getByRole('button', { name: /2026-05-15/ })
    fireEvent.click(result)
    expect(onSelect).toHaveBeenCalledWith('2026-05-15')
  })

  it('닫기 버튼 클릭 시 onClose 호출', () => {
    const onClose = vi.fn()
    render(<SearchModal entries={ENTRIES} onClose={onClose} onSelect={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(onClose).toHaveBeenCalled()
  })
})
