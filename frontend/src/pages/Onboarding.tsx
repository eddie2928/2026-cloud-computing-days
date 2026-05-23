import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { ScreenContainer } from '../components/days/ScreenContainer'
import { ProgressBar } from '../components/days/ProgressBar'
import { PillButton } from '../components/days/PillButton'
import { BoxInput } from '../components/days/BoxInput'
import { Chip } from '../components/days/Chip'
import { FieldLabel } from '../components/days/FieldLabel'
import { SoftBackdrop } from '../components/days/SoftBackdrop'
import { TagInput } from '../components/days/TagInput'

interface FormData {
  nickname: string
  gender: string
  age: string
  occupation: string
  hobbies: string[]
  interests: string[]
}

export function Onboarding() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [ready, setReady] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState<FormData>({
    nickname: '',
    gender: '',
    age: '',
    occupation: '',
    hobbies: [],
    interests: [],
  })

  useEffect(() => {
    client.get('/profile').then(() => {
      navigate('/hub', { replace: true })
    }).catch((e) => {
      if (e.response?.status === 404) setReady(true)
    })
  }, [navigate])

  const handleFinish = async () => {
    setSubmitting(true)
    try {
      await client.put('/profile', {
        nickname: form.nickname,
        gender: form.gender,
        age: Number(form.age) || 0,
        occupation: form.occupation,
        hobbies: form.hobbies,
        interests: form.interests,
      })
      navigate('/hub')
    } catch {
      setSubmitting(false)
    }
  }

  if (!ready) return <div style={{ fontFamily: 'var(--font-sans)', padding: 24 }}>Loading...</div>

  return (
    <ScreenContainer style={{ background: 'var(--paper-bone)', position: 'relative' }}>
      <SoftBackdrop variant="app" />
      <div style={{ position: 'relative', zIndex: 1, padding: '48px 24px 32px', flex: 1, display: 'flex', flexDirection: 'column', gap: 32 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-xs)', color: 'var(--ink-meta)', fontWeight: 500 }}>
            {step} / 3단계
          </span>
          <ProgressBar value={step} max={3} />
          <h2 style={{ margin: 0, fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 'var(--t-xl)', color: 'var(--sage-ink)', letterSpacing: '-0.01em' }}>
            {step === 1 && '기본 정보를 알려주세요'}
            {step === 2 && '어떤 일을 하세요?'}
            {step === 3 && '관심사를 알려주세요'}
          </h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, flex: 1 }}>
          {step === 1 && (
            <>
              <div>
                <FieldLabel required>닉네임</FieldLabel>
                <BoxInput value={form.nickname} onChange={v => setForm(f => ({ ...f, nickname: v }))} placeholder="예: 지민" ariaLabel="닉네임" />
              </div>
              <div>
                <FieldLabel required>성별</FieldLabel>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['male', 'female', 'other'].map(g => (
                    <Chip key={g} variant="segment" active={form.gender === g} onClick={() => setForm(f => ({ ...f, gender: g }))}>
                      {g === 'male' ? '남성' : g === 'female' ? '여성' : '기타'}
                    </Chip>
                  ))}
                </div>
              </div>
              <div>
                <FieldLabel required>나이</FieldLabel>
                <BoxInput value={form.age} onChange={v => setForm(f => ({ ...f, age: v }))} placeholder="예: 25" type="number" ariaLabel="나이" />
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <div>
                <FieldLabel>직업</FieldLabel>
                <BoxInput value={form.occupation} onChange={v => setForm(f => ({ ...f, occupation: v }))} placeholder="예: 대학생, 개발자" ariaLabel="직업" />
              </div>
              <div>
                <FieldLabel>취미 (키워드 입력)</FieldLabel>
                <TagInput
                  value={form.hobbies}
                  onChange={v => setForm(f => ({ ...f, hobbies: v }))}
                  placeholder="예: 독서"
                  ariaLabel="취미"
                />
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div>
                <FieldLabel>관심사 (키워드 입력)</FieldLabel>
                <TagInput
                  value={form.interests}
                  onChange={v => setForm(f => ({ ...f, interests: v }))}
                  placeholder="예: 건강"
                  ariaLabel="관심사"
                />
              </div>
              {/* TODO: Phase 3 추후 구현 예정
              <div>
                <FieldLabel>일기 알림 시간</FieldLabel>
                <BoxInput value={form.notification_time} onChange={v => setForm(f => ({ ...f, notification_time: v }))} type="time" ariaLabel="알림 시간" />
              </div>
              */}
            </>
          )}
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          {step > 1 && (
            <PillButton variant="ghost" full={false} onClick={() => setStep(s => s - 1)} style={{ flex: 1 }}>
              이전
            </PillButton>
          )}
          {step < 3 ? (
            <PillButton onClick={() => setStep(s => s + 1)} disabled={step === 1 && (!form.nickname || !form.gender || !form.age)} style={{ flex: 1 }}>
              다음
            </PillButton>
          ) : (
            <PillButton onClick={handleFinish} disabled={submitting} style={{ flex: 1 }}>
              {submitting ? '저장 중...' : '시작하기'}
            </PillButton>
          )}
        </div>
      </div>
    </ScreenContainer>
  )
}
