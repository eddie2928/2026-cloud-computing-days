import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { Admin } from '../src/pages/Admin'

const server = setupServer(
  http.get('/api/admin/tables/users', () =>
    HttpResponse.json([
      { id: 1, display_name: '테스트유저', created_at: '2026-05-01T00:00:00Z' },
    ])
  ),
  http.get('/api/admin/tables/diary_entries', () =>
    HttpResponse.json([
      { id: 1, user_id: 1, diary_date: '2026-05-01', body: '일기 본문', summary: '요약', emotion: 'happy' },
    ])
  )
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Admin page', () => {
  it('fetches and renders rows when table is selected', async () => {
    render(<Admin />)

    // Default table is users - rows should load
    await waitFor(() => {
      expect(screen.getByText('테스트유저')).toBeDefined()
    })

    // Columns from first row should appear as headers
    expect(screen.getByText('id')).toBeDefined()
    expect(screen.getByText('display_name')).toBeDefined()
  })
})
