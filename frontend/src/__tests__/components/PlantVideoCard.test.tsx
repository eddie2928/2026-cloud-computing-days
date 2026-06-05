/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { PlantVideoCard } from '../../components/hub/PlantVideoCard'

vi.mock('../../hooks/useMockDate', () => ({
  useMockDate: vi.fn().mockReturnValue('2026-01-15'), // winter by default
}))

describe('PlantVideoCard season prop', () => {
  it('uses season prop instead of date-derived season', () => {
    const { container } = render(<PlantVideoCard plantState={2} season="summer" />)
    const source = container.querySelector('source')
    expect(source?.getAttribute('src')).toBe('/videos/plant-summer-2.mp4')
  })

  it('falls back to date-derived season when prop is absent', () => {
    // useMockDate returns 2026-01-15 → winter
    const { container } = render(<PlantVideoCard plantState={1} />)
    const source = container.querySelector('source')
    expect(source?.getAttribute('src')).toBe('/videos/plant-winter.mp4')
  })

  it('renders correct src for spring / state 3', () => {
    const { container } = render(<PlantVideoCard plantState={3} season="spring" />)
    const source = container.querySelector('source')
    expect(source?.getAttribute('src')).toBe('/videos/plant-spring-3.mp4')
  })
})
