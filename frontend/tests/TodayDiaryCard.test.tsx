import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { TodayDiaryCard } from '../src/components/hub/TodayDiaryCard'

const TODAY = '2026-05-22'

describe('TodayDiaryCard', () => {
  it('hasDiary=false → "오늘의 일기 시작" 버튼 표시', () => {
    render(
      <MemoryRouter>
        <TodayDiaryCard today={TODAY} hasDiary={false} onOpen={() => {}} />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: '오늘의 일기 시작' })).toBeInTheDocument()
  })

  it('hasDiary=true → "이어보기" 버튼 + 요약 표시', () => {
    render(
      <MemoryRouter>
        <TodayDiaryCard today={TODAY} hasDiary summary="오늘은 좋은 하루였습니다." onOpen={() => {}} />
      </MemoryRouter>
    )
    expect(screen.getByRole('button', { name: '이어보기' })).toBeInTheDocument()
    expect(screen.getByText('오늘은 좋은 하루였습니다.')).toBeInTheDocument()
  })
})
