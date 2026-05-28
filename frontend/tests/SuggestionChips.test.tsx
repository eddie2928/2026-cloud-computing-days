import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SuggestionChips } from '../src/components/qna/SuggestionChips'

describe('SuggestionChips', () => {
  it('renders 3 chips when given 3 suggestions', () => {
    render(<SuggestionChips suggestions={['a', 'b', 'c']} onPick={vi.fn()} />)
    expect(screen.getByText('a')).toBeInTheDocument()
    expect(screen.getByText('b')).toBeInTheDocument()
    expect(screen.getByText('c')).toBeInTheDocument()
  })

  it('returns null when suggestions is empty', () => {
    const { container } = render(<SuggestionChips suggestions={[]} onPick={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls onPick with chip text when clicked', () => {
    const onPick = vi.fn()
    render(<SuggestionChips suggestions={['답변1']} onPick={onPick} />)
    fireEvent.click(screen.getByText('답변1'))
    expect(onPick).toHaveBeenCalledWith('답변1')
  })

  it('does not call onPick when disabled', () => {
    const onPick = vi.fn()
    render(<SuggestionChips suggestions={['답변1']} onPick={onPick} disabled />)
    fireEvent.click(screen.getByText('답변1'))
    expect(onPick).not.toHaveBeenCalled()
  })
})
