import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PetCard } from '../src/components/hub/PetCard'

describe('PetCard', () => {
  it('placeholder 텍스트 렌더', () => {
    render(<PetCard />)
    expect(screen.getByText('다마고치가 곧 찾아와요')).toBeInTheDocument()
  })
})
