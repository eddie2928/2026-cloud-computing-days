import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenContainer } from '../components/days/ScreenContainer'
import { ProgressBar } from '../components/days/ProgressBar'
import { PillButton } from '../components/days/PillButton'
import { BoxInput } from '../components/days/BoxInput'
import { Chip } from '../components/days/Chip'
import { FieldLabel } from '../components/days/FieldLabel'
import { SoftBackdrop } from '../components/days/SoftBackdrop'
import { TagInput } from '../components/days/TagInput'
import { getTasteProfile, putTasteProfile } from '../api/taste'
import {
  EMPTY_TASTE_FORM,
  MUSIC_GENRE_OPTIONS,
  MUSIC_MOOD_OPTIONS,
  MBTI_OPTIONS,
  MOVIE_GENRE_OPTIONS,
  LIFE_VALUE_OPTIONS,
  WEEKEND_STYLE_OPTIONS,
  LOVE_LANGUAGE_OPTIONS,
  type TasteFormData,
} from '../lib/taste'

const TOTAL_STEPS = 11

function toggleItem(arr: string[], item: string): string[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item]
}

export function TasteSurvey() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<TasteFormData>(EMPTY_TASTE_FORM)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getTasteProfile()
      .then((data) => {
        setForm({
          music_genres: data.music_genres ?? [],
          favorite_artists: data.favorite_artists ?? [],
          preferred_music_mood: data.preferred_music_mood ?? [],
          mbti: data.mbti ?? '',
          ideal_type: data.ideal_type ?? '',
          personality_keywords: data.personality_keywords ?? [],
          movie_genres: data.movie_genres ?? [],
          food_preferences: data.food_preferences ?? [],
          weekend_style: data.weekend_style ?? '',
          life_values: data.life_values ?? [],
          love_language: data.love_language ?? '',
        })
      })
      .catch((e) => {
        if (e.response?.status !== 404) console.error(e)
      })
      .finally(() => setLoading(false))
  }, [])

  const handleFinish = async () => {
    setSubmitting(true)
    try {
      await putTasteProfile({
        ...form,
        mbti: form.mbti === '모름' ? '' : form.mbti,
      })
      navigate('/profile')
    } catch {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div style={{ fontFamily: 'var(--font-sans)', padding: 24, color: 'var(--ink-meta)' }}>
        로딩 중...
      </div>
    )
  }

  const stepLabel = (s: number) => {
    const labels: Record<number, string> = {
      1: '좋아하는 음악 장르를 선택해주세요',
      2: '좋아하는 아티스트를 알려주세요',
      3: '선호하는 음악 분위기는?',
      4: '나의 MBTI는?',
      5: '이상형을 자유롭게 서술해주세요',
      6: '나를 표현하는 성격 키워드',
      7: '좋아하는 영화·콘텐츠 장르',
      8: '음식 취향을 알려주세요',
      9: '주말에 주로 무엇을 하나요?',
      10: '중요하게 여기는 가치는?',
      11: '애정표현 방식은?',
    }
    return labels[s] ?? ''
  }

  return (
    <ScreenContainer style={{ background: 'var(--paper-bone)', position: 'relative' }}>
      <SoftBackdrop variant="app" />
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          padding: '48px 24px 32px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: 28,
          animation: 'days-fade-in 500ms var(--ease-out) both',
        }}
      >
        {/* 헤더 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span
            style={{
              font: '500 13px/1 var(--font-sans)',
              color: 'var(--ink-meta)',
            }}
          >
            {step} / {TOTAL_STEPS}단계
          </span>
          <ProgressBar value={step} max={TOTAL_STEPS} />
          <h2
            style={{
              margin: 0,
              font: '700 22px/1.3 var(--font-sans)',
              color: 'var(--sage-ink)',
              letterSpacing: '-0.01em',
            }}
          >
            {stepLabel(step)}
          </h2>
        </div>

        {/* 각 단계 콘텐츠 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {step === 1 && (
            <Step1
              value={form.music_genres}
              onChange={(v) => setForm((f) => ({ ...f, music_genres: v }))}
            />
          )}
          {step === 2 && (
            <Step2
              value={form.favorite_artists}
              onChange={(v) => setForm((f) => ({ ...f, favorite_artists: v }))}
            />
          )}
          {step === 3 && (
            <Step3
              value={form.preferred_music_mood}
              onChange={(v) => setForm((f) => ({ ...f, preferred_music_mood: v }))}
            />
          )}
          {step === 4 && (
            <Step4
              value={form.mbti}
              onChange={(v) => setForm((f) => ({ ...f, mbti: v }))}
            />
          )}
          {step === 5 && (
            <Step5
              value={form.ideal_type}
              onChange={(v) => setForm((f) => ({ ...f, ideal_type: v }))}
            />
          )}
          {step === 6 && (
            <Step6
              value={form.personality_keywords}
              onChange={(v) => setForm((f) => ({ ...f, personality_keywords: v }))}
            />
          )}
          {step === 7 && (
            <Step7
              value={form.movie_genres}
              onChange={(v) => setForm((f) => ({ ...f, movie_genres: v }))}
            />
          )}
          {step === 8 && (
            <Step8
              value={form.food_preferences}
              onChange={(v) => setForm((f) => ({ ...f, food_preferences: v }))}
            />
          )}
          {step === 9 && (
            <Step9
              value={form.weekend_style}
              onChange={(v) => setForm((f) => ({ ...f, weekend_style: v }))}
            />
          )}
          {step === 10 && (
            <Step10
              value={form.life_values}
              onChange={(v) => setForm((f) => ({ ...f, life_values: v }))}
            />
          )}
          {step === 11 && (
            <Step11
              value={form.love_language}
              onChange={(v) => setForm((f) => ({ ...f, love_language: v }))}
            />
          )}
        </div>

        {/* 하단 네비게이션 */}
        <div style={{ display: 'flex', gap: 12 }}>
          {step > 1 ? (
            <PillButton
              variant="ghost"
              full={false}
              onClick={() => setStep((s) => s - 1)}
              style={{ flex: 1 }}
            >
              이전
            </PillButton>
          ) : (
            <PillButton
              variant="ghost"
              full={false}
              onClick={() => navigate('/profile')}
              style={{ flex: 1 }}
            >
              취소
            </PillButton>
          )}
          {step < TOTAL_STEPS ? (
            <PillButton onClick={() => setStep((s) => s + 1)} style={{ flex: 1 }}>
              다음
            </PillButton>
          ) : (
            <PillButton onClick={handleFinish} disabled={submitting} style={{ flex: 1 }}>
              {submitting ? '저장 중...' : '저장하기'}
            </PillButton>
          )}
        </div>
      </div>
    </ScreenContainer>
  )
}

/* ─── Step sub-components ─── */

function ChipGroup({
  options,
  value,
  onChange,
}: {
  options: string[]
  value: string[]
  onChange: (v: string[]) => void
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {options.map((opt) => (
        <Chip
          key={opt}
          variant="pill"
          active={value.includes(opt)}
          onClick={() => onChange(toggleItem(value, opt))}
        >
          {opt}
        </Chip>
      ))}
    </div>
  )
}

function SingleChipGroup({
  options,
  value,
  onChange,
}: {
  options: string[]
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {options.map((opt) => (
        <Chip
          key={opt}
          variant="pill"
          active={value === opt}
          onClick={() => onChange(value === opt ? '' : opt)}
        >
          {opt}
        </Chip>
      ))}
    </div>
  )
}

function Step1({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>장르 선택 (복수 가능)</FieldLabel>
      <ChipGroup options={MUSIC_GENRE_OPTIONS} value={value} onChange={onChange} />
    </>
  )
}

function Step2({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>아티스트 입력 (Enter로 추가)</FieldLabel>
      <TagInput value={value} onChange={onChange} placeholder="예: 아이유, BTS" ariaLabel="좋아하는 아티스트" />
    </>
  )
}

function Step3({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>분위기 선택 (복수 가능)</FieldLabel>
      <ChipGroup options={MUSIC_MOOD_OPTIONS} value={value} onChange={onChange} />
    </>
  )
}

function Step4({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <>
      <FieldLabel>MBTI 선택</FieldLabel>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
        }}
      >
        {MBTI_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => onChange(value === opt ? '' : opt)}
            style={{
              padding: '10px 4px',
              borderRadius: 12,
              border: value === opt ? '0' : '1.5px solid var(--line)',
              background: value === opt ? 'var(--sage-leaf)' : 'var(--paper-pure)',
              color: value === opt ? 'var(--paper-pure)' : 'var(--ink-body)',
              font: '500 14px/1 var(--font-sans)',
              cursor: 'pointer',
              transition: 'background var(--dur-1), color var(--dur-1)',
            }}
          >
            {opt}
          </button>
        ))}
      </div>
    </>
  )
}

function Step5({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [focused, setFocused] = useState(false)
  return (
    <>
      <FieldLabel>이상형 (자유 서술)</FieldLabel>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="예: 배려심 있고 유머 감각이 있는 사람"
        aria-label="이상형 서술"
        rows={5}
        style={{
          width: '100%',
          padding: '12px 16px',
          borderRadius: 16,
          border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
          background: 'var(--paper-bone)',
          font: '400 15px/1.6 var(--font-sans)',
          color: 'var(--ink-deep)',
          outline: 'none',
          resize: 'vertical',
          boxSizing: 'border-box',
          boxShadow: focused ? 'var(--shadow-ring)' : 'none',
          transition: 'border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out)',
        }}
      />
    </>
  )
}

function Step6({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>성격 키워드 입력 (Enter로 추가)</FieldLabel>
      <TagInput value={value} onChange={onChange} placeholder="예: 따뜻함, 내향적" ariaLabel="성격 키워드" />
    </>
  )
}

function Step7({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>장르 선택 (복수 가능)</FieldLabel>
      <ChipGroup options={MOVIE_GENRE_OPTIONS} value={value} onChange={onChange} />
    </>
  )
}

function Step8({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>음식 취향 입력 (Enter로 추가)</FieldLabel>
      <TagInput value={value} onChange={onChange} placeholder="예: 매운 음식, 초밥" ariaLabel="음식 취향" />
    </>
  )
}

function Step9({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <>
      <FieldLabel>주말 성향 선택</FieldLabel>
      <SingleChipGroup options={WEEKEND_STYLE_OPTIONS} value={value} onChange={onChange} />
      <div style={{ marginTop: 8 }}>
        <BoxInput
          value={value && !WEEKEND_STYLE_OPTIONS.includes(value) ? value : ''}
          onChange={(v) => onChange(v)}
          placeholder="직접 입력 (선택 사항)"
          ariaLabel="주말 성향 직접 입력"
        />
      </div>
    </>
  )
}

function Step10({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <>
      <FieldLabel>가치관 선택 (복수 가능)</FieldLabel>
      <ChipGroup options={LIFE_VALUE_OPTIONS} value={value} onChange={onChange} />
    </>
  )
}

function Step11({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <>
      <FieldLabel>애정표현 방식 선택</FieldLabel>
      <SingleChipGroup options={LOVE_LANGUAGE_OPTIONS} value={value} onChange={onChange} />
      <div style={{ marginTop: 8 }}>
        <BoxInput
          value={value && !LOVE_LANGUAGE_OPTIONS.includes(value) ? value : ''}
          onChange={(v) => onChange(v)}
          placeholder="직접 입력 (선택 사항)"
          ariaLabel="애정표현 방식 직접 입력"
        />
      </div>
    </>
  )
}
