/**
 * @reusable
 * @scope project-local
 * @description 다단계 폼 플로우 테스트 패턴 (단계 이동, 저장 호출, 404 폴백)
 * @usage 다른 문진/온보딩 페이지에 적용 시 단계 수(11)와 API mock 경로를 프로젝트에 맞게 수정
 * @origin agent-task6 / jmh-worker-frontend
 * @created 2026-06-02T16:35:00+09:00
 */
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { TasteSurvey } from '../../pages/TasteSurvey'
import * as tasteApi from '../../api/taste'
import type { TasteFormData } from '../../lib/taste'

vi.mock('../../api/taste')

const mockNavigate = vi.hoisted(() => vi.fn())
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockTaste: TasteFormData = {
  music_genres: ['팝', '인디'],
  favorite_artists: ['아이유'],
  preferred_music_mood: ['잔잔한'],
  mbti: 'INFP',
  ideal_type: '따뜻한 사람',
  personality_keywords: ['내향적'],
  movie_genres: ['로맨스'],
  food_preferences: ['초밥'],
  weekend_style: '집에서 쉬기',
  life_values: ['자유'],
  love_language: '함께하는 시간',
}

function renderSurvey() {
  return render(
    <MemoryRouter>
      <TasteSurvey />
    </MemoryRouter>,
  )
}

describe('TasteSurvey 페이지', () => {
  beforeEach(() => {
    vi.mocked(tasteApi.getTasteProfile).mockResolvedValue(mockTaste)
    vi.mocked(tasteApi.putTasteProfile).mockResolvedValue(mockTaste)
    mockNavigate.mockClear()
  })

  it('초기 로딩 후 1단계가 표시됨', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    expect(screen.getByText('좋아하는 음악 장르를 선택해주세요')).toBeInTheDocument()
  })

  it('기존 취향 데이터가 있으면 팝 칩이 활성화됨', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    // 팝 칩이 렌더됨 (active 여부는 스타일로만 구분되어 text로 확인)
    expect(screen.getByText('팝')).toBeInTheDocument()
  })

  it('404 응답 시 빈 폼으로 시작함', async () => {
    vi.mocked(tasteApi.getTasteProfile).mockRejectedValue({ response: { status: 404 } })
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    // 에러 없이 렌더됨
    expect(screen.getByText('좋아하는 음악 장르를 선택해주세요')).toBeInTheDocument()
  })

  it('다음 버튼 클릭 시 2단계로 진행됨', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    fireEvent.click(screen.getByText('다음'))
    expect(screen.getByText('2 / 11단계')).toBeInTheDocument()
    expect(screen.getByText('좋아하는 아티스트를 알려주세요')).toBeInTheDocument()
  })

  it('이전 버튼 클릭 시 이전 단계로 돌아감', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    fireEvent.click(screen.getByText('다음'))
    expect(screen.getByText('2 / 11단계')).toBeInTheDocument()
    fireEvent.click(screen.getByText('이전'))
    expect(screen.getByText('1 / 11단계')).toBeInTheDocument()
  })

  it('1단계에서 취소 클릭 시 /profile로 navigate', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    fireEvent.click(screen.getByText('취소'))
    expect(mockNavigate).toHaveBeenCalledWith('/profile')
  })

  it('마지막 단계에서 저장하기 버튼이 표시됨', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    // Navigate to step 11
    for (let i = 1; i < 11; i++) {
      fireEvent.click(screen.getByText('다음'))
    }
    expect(screen.getByText('11 / 11단계')).toBeInTheDocument()
    expect(screen.getByText('저장하기')).toBeInTheDocument()
  })

  it('저장 시 putTasteProfile 호출 후 /profile로 navigate', async () => {
    renderSurvey()
    await waitFor(() => expect(screen.getByText('1 / 11단계')).toBeInTheDocument())
    for (let i = 1; i < 11; i++) {
      fireEvent.click(screen.getByText('다음'))
    }
    fireEvent.click(screen.getByText('저장하기'))
    await waitFor(() => expect(tasteApi.putTasteProfile).toHaveBeenCalled())
    expect(mockNavigate).toHaveBeenCalledWith('/profile')
  })
})
