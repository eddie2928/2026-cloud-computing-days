import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, it, expect } from 'vitest'
import { PetCard } from '../src/components/hub/PetCard'
import { server } from './setup'

describe('PetCard', () => {
  it('level=1 → 🥚 렌더', async () => {
    render(<PetCard />)
    await waitFor(() => {
      expect(screen.getByText('레벨 1')).toBeInTheDocument()
    })
  })

  it('level=2 → 🐣 렌더', async () => {
    server.use(http.get('/api/pet', () => HttpResponse.json({ level: 2, xp: 50, xp_to_next: 100 })))
    render(<PetCard />)
    await waitFor(() => {
      expect(screen.getByText('레벨 2')).toBeInTheDocument()
    })
    expect(screen.getByText('50/100')).toBeInTheDocument()
  })

  it('level=5+ → 🐔 렌더', async () => {
    server.use(http.get('/api/pet', () => HttpResponse.json({ level: 7, xp: 30, xp_to_next: 100 })))
    render(<PetCard />)
    await waitFor(() => {
      expect(screen.getByText('레벨 7')).toBeInTheDocument()
    })
  })
})
