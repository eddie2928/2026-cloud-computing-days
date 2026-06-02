/**
 * @reusable
 * @scope project-local
 * @description 상수 옵션 및 기본값 불변 검증 패턴 (배열 길이, 포함 여부, 빈 기본값)
 * @usage 다른 lib 상수 파일 테스트 시 import 경로와 상수명만 교체
 * @origin agent-task6 / jmh-worker-frontend
 * @created 2026-06-02T16:35:00+09:00
 */
import { describe, it, expect } from 'vitest'
import {
  EMPTY_TASTE_FORM,
  MUSIC_GENRE_OPTIONS,
  MBTI_OPTIONS,
  MUSIC_MOOD_OPTIONS,
  MOVIE_GENRE_OPTIONS,
  LIFE_VALUE_OPTIONS,
  WEEKEND_STYLE_OPTIONS,
  LOVE_LANGUAGE_OPTIONS,
} from '../../lib/taste'

describe('lib/taste 상수 및 기본값', () => {
  it('EMPTY_TASTE_FORM은 모든 배열이 빈 배열이고 문자열이 빈 문자열', () => {
    expect(EMPTY_TASTE_FORM.music_genres).toEqual([])
    expect(EMPTY_TASTE_FORM.favorite_artists).toEqual([])
    expect(EMPTY_TASTE_FORM.preferred_music_mood).toEqual([])
    expect(EMPTY_TASTE_FORM.mbti).toBe('')
    expect(EMPTY_TASTE_FORM.ideal_type).toBe('')
    expect(EMPTY_TASTE_FORM.personality_keywords).toEqual([])
    expect(EMPTY_TASTE_FORM.movie_genres).toEqual([])
    expect(EMPTY_TASTE_FORM.food_preferences).toEqual([])
    expect(EMPTY_TASTE_FORM.weekend_style).toBe('')
    expect(EMPTY_TASTE_FORM.life_values).toEqual([])
    expect(EMPTY_TASTE_FORM.love_language).toBe('')
  })

  it('MUSIC_GENRE_OPTIONS에 최소 10개 항목이 있음', () => {
    expect(MUSIC_GENRE_OPTIONS.length).toBeGreaterThanOrEqual(10)
  })

  it('MBTI_OPTIONS에 16개 유형 + 모름 = 17개 항목', () => {
    expect(MBTI_OPTIONS).toContain('INFP')
    expect(MBTI_OPTIONS).toContain('ENTJ')
    expect(MBTI_OPTIONS).toContain('모름')
    expect(MBTI_OPTIONS.length).toBe(17)
  })

  it('MUSIC_MOOD_OPTIONS에 잔잔한, 신나는 포함', () => {
    expect(MUSIC_MOOD_OPTIONS).toContain('잔잔한')
    expect(MUSIC_MOOD_OPTIONS).toContain('신나는')
  })

  it('MOVIE_GENRE_OPTIONS, LIFE_VALUE_OPTIONS, WEEKEND_STYLE_OPTIONS, LOVE_LANGUAGE_OPTIONS 모두 비어있지 않음', () => {
    expect(MOVIE_GENRE_OPTIONS.length).toBeGreaterThan(0)
    expect(LIFE_VALUE_OPTIONS.length).toBeGreaterThan(0)
    expect(WEEKEND_STYLE_OPTIONS.length).toBeGreaterThan(0)
    expect(LOVE_LANGUAGE_OPTIONS.length).toBeGreaterThan(0)
  })
})
