/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Admin } from '../../pages/Admin'
import * as musicApi from '../../api/music'

vi.mock('../../api/music')
vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}))
vi.mock('../../lib/push', () => ({
  getPushState: vi.fn().mockResolvedValue('not-subscribed'),
  subscribePush: vi.fn(),
}))
vi.mock('../../lib/mockDate', () => ({
  getMockDate: vi.fn().mockReturnValue(''),
  setMockDate: vi.fn(),
  clearMockDate: vi.fn(),
  hasMockDate: vi.fn().mockReturnValue(false),
}))

const mockSuccessResult: musicApi.MusicSearchResult = {
  ok: true,
  status_code: 200,
  latency_ms: 123,
  count: 1,
  results: [
    {
      trackName: 'LILAC',
      artistName: 'IU',
      previewUrl: 'https://audio.example.com/preview.m4a',
      artworkUrl100: 'https://img.example.com/artwork.jpg',
      collectionName: 'LILAC',
      trackViewUrl: 'https://music.apple.com/track/123',
    },
  ],
}

const mockFailResult: musicApi.MusicSearchResult = {
  ok: false,
  status_code: null,
  latency_ms: 50,
  results: [],
  error: '네트워크 오류',
}

function renderAdmin() {
  return render(
    <MemoryRouter>
      <Admin />
    </MemoryRouter>
  )
}

describe('Admin 음악 API 탭', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('탭 버튼 "음악 API"가 렌더링된다', () => {
    renderAdmin()
    expect(screen.getByRole('button', { name: '음악 API' })).toBeInTheDocument()
  })

  it('음악 API 탭 클릭 시 검색 입력 UI가 표시된다', () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: '음악 API' }))
    expect(screen.getByPlaceholderText(/예: IU/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /검색 \/ 통신 테스트/ })).toBeInTheDocument()
  })

  it('검색어 없으면 검색 버튼이 비활성화된다', () => {
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: '음악 API' }))
    const searchBtn = screen.getByRole('button', { name: /검색 \/ 통신 테스트/ })
    expect(searchBtn).toBeDisabled()
  })

  it('성공 응답 시 결과 패널에 성공 배지와 트랙을 렌더링한다', async () => {
    vi.mocked(musicApi.searchMusic).mockResolvedValue(mockSuccessResult)
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: '음악 API' }))

    const input = screen.getByPlaceholderText(/예: IU/)
    fireEvent.change(input, { target: { value: 'IU' } })
    fireEvent.click(screen.getByRole('button', { name: /검색 \/ 통신 테스트/ }))

    await waitFor(() => {
      expect(screen.getByText('성공')).toBeInTheDocument()
    })
    expect(screen.getAllByText('LILAC').length).toBeGreaterThan(0)
    expect(screen.getByText('IU')).toBeInTheDocument()
    expect(screen.getByText('123 ms')).toBeInTheDocument()
    expect(screen.getByText('1건')).toBeInTheDocument()
  })

  it('실패 응답 시 실패 배지와 에러 메시지를 표시한다', async () => {
    vi.mocked(musicApi.searchMusic).mockResolvedValue(mockFailResult)
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: '음악 API' }))

    const input = screen.getByPlaceholderText(/예: IU/)
    fireEvent.change(input, { target: { value: 'test' } })
    fireEvent.click(screen.getByRole('button', { name: /검색 \/ 통신 테스트/ }))

    await waitFor(() => {
      expect(screen.getByText('실패')).toBeInTheDocument()
    })
    expect(screen.getByText('네트워크 오류')).toBeInTheDocument()
  })

  it('Raw 토글 클릭 시 JSON 원본을 표시한다', async () => {
    vi.mocked(musicApi.searchMusic).mockResolvedValue(mockSuccessResult)
    renderAdmin()
    fireEvent.click(screen.getByRole('button', { name: '음악 API' }))

    const input = screen.getByPlaceholderText(/예: IU/)
    fireEvent.change(input, { target: { value: 'IU' } })
    fireEvent.click(screen.getByRole('button', { name: /검색 \/ 통신 테스트/ }))

    await waitFor(() => expect(screen.getByText('성공')).toBeInTheDocument())

    const rawBtn = screen.getByRole('button', { name: 'Raw' })
    fireEvent.click(rawBtn)

    await waitFor(() => {
      expect(screen.getByText(/trackName/)).toBeInTheDocument()
    })
  })
})
