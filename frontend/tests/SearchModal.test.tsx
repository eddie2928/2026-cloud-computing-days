import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SearchModal } from '../src/components/search/SearchModal'

vi.mock('../src/lib/search', () => ({
  searchDiaries: vi.fn().mockResolvedValue([
    { date: '2026-05-15', snippet: '오늘은 산책을 했다', emotion: 'happy' },
  ]),
}))

describe('SearchModal', () => {
  it('검색어 입력 후 debounce → API 결과 + snippet 렌더 + onSelect 호출', async () => {
    vi.useFakeTimers()
    const onSelect = vi.fn()
    const onClose = vi.fn()
    render(<SearchModal onClose={onClose} onSelect={onSelect} />)
    const input = screen.getByLabelText('일기 검색 입력') as HTMLInputElement
    fireEvent.change(input, { target: { value: '산책' } })

    await act(async () => {
      vi.advanceTimersByTime(300)
    })
    vi.useRealTimers()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /2026-05-15/ })).toBeInTheDocument()
    })

    const result = screen.getByRole('button', { name: /2026-05-15/ })
    fireEvent.click(result)
    expect(onSelect).toHaveBeenCalledWith('2026-05-15')
  })

  it('닫기 버튼 클릭 시 onClose 호출', () => {
    const onClose = vi.fn()
    render(<SearchModal onClose={onClose} onSelect={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(onClose).toHaveBeenCalled()
  })
})
