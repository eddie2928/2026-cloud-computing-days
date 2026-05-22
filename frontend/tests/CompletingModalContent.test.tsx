import { render } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { CompletingModalContent } from '../src/components/calendar/CompletingModalContent'

describe('CompletingModalContent', () => {
  it('지정 시간 후 onDone 호출', async () => {
    vi.useFakeTimers()
    const onDone = vi.fn()
    render(<CompletingModalContent onDone={onDone} durationMs={1500} />)
    expect(onDone).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1500)
    expect(onDone).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})
