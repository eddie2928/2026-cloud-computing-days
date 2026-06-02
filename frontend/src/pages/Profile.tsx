import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { Header } from '../components/layout/Header'
import { SectionCard } from '../components/profile/SectionCard'
import { FieldRow } from '../components/profile/FieldRow'
import { BoxInput } from '../components/days/BoxInput'
import { Chip } from '../components/days/Chip'
import { PillButton } from '../components/days/PillButton'
import { CloudLeaf } from '../components/days/CloudLeaf'
import { TagInput } from '../components/days/TagInput'
import { getPushState, subscribePush, unsubscribePush, type PushState } from '../lib/push'
import { useInstallPrompt } from '../hooks/useInstallPrompt'
import { InstallGuideModal } from '../components/days/InstallGuideModal'
import { Icon } from '../components/days/Icon'
import { getTasteProfile } from '../api/taste'
import type { TasteFormData } from '../lib/taste'

interface ProfileData {
  nickname: string
  gender: string
  age: number | ''
  occupation: string
  hobbies: string[]
  interests: string[]
  notification_time: string | null
}

export function Profile() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [data, setData] = useState<ProfileData | null>(null)
  const [draft, setDraft] = useState<ProfileData | null>(null)
  const [saving, setSaving] = useState(false)
  const [pushState, setPushState] = useState<PushState>('default')
  const [tasteProfile, setTasteProfile] = useState<TasteFormData | null>(null)
  const [tasteLoading, setTasteLoading] = useState(true)
  const [pushLoading, setPushLoading] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const { canInstall, isIOSSafari, isStandalone, promptInstall } = useInstallPrompt()

  useEffect(() => {
    client.get('/profile').then((res) => {
      const d = res.data
      const p: ProfileData = {
        nickname: d.nickname ?? '',
        gender: d.gender ?? '',
        age: d.age ?? '',
        occupation: d.occupation ?? '',
        hobbies: d.hobbies ?? [],
        interests: d.interests ?? [],
        notification_time: d.notification_time ?? null,
      }
      setData(p)
      setDraft({ ...p })
    }).catch((e) => {
      if (e.response?.status === 404) navigate('/onboarding', { replace: true })
    })
  }, [navigate])

  const save = async () => {
    if (!draft) return
    setSaving(true)
    try {
      await client.put('/profile', {
        nickname: draft.nickname,
        gender: draft.gender,
        age: Number(draft.age) || 0,
        occupation: draft.occupation,
        hobbies: draft.hobbies,
        interests: draft.interests,
      })
      setData({ ...draft })
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    getPushState().then(setPushState)
  }, [])

  useEffect(() => {
    getTasteProfile()
      .then(setTasteProfile)
      .catch(() => setTasteProfile(null))
      .finally(() => setTasteLoading(false))
  }, [])

  const handlePushToggle = async () => {
    setPushLoading(true)
    try {
      if (pushState === 'subscribed') {
        await unsubscribePush()
      } else {
        await subscribePush()
      }
      setPushState(await getPushState())
    } catch {
      setPushState(await getPushState())
    } finally {
      setPushLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  if (!data || !draft) return <div style={{ fontFamily: 'var(--font-sans)', padding: 24 }}>Loading...</div>

  const genderLabel = (g: string) => g === 'male' ? '남성' : g === 'female' ? '여성' : g === 'other' ? '기타' : g

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%' }}>
      <Header title="프로필" showBack />

      {/* 아바타 + 닉네임 */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '24px 0 16px' }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%',
          background: 'var(--sage-wash)',
          border: '2px solid var(--sage-mist)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <CloudLeaf size={54} color="var(--sage-forest)" stroke={2.5} />
        </div>
        <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 'var(--t-lg)', color: 'var(--sage-ink)' }}>
          {data.nickname || '닉네임 없음'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '8px 16px 24px' }}>
        <SectionCard
          title="기본 정보"
          editContent={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <BoxInput value={String(draft.nickname)} onChange={v => setDraft(f => f && ({ ...f, nickname: v }))} placeholder="닉네임" ariaLabel="닉네임 수정" />
              <div style={{ display: 'flex', gap: 8 }}>
                {['male', 'female', 'other'].map(g => (
                  <Chip key={g} variant="segment" active={draft.gender === g} onClick={() => setDraft(f => f && ({ ...f, gender: g }))}>
                    {genderLabel(g)}
                  </Chip>
                ))}
              </div>
              <BoxInput value={String(draft.age)} onChange={v => setDraft(f => f && ({ ...f, age: v === '' ? '' : Number(v) }))} placeholder="나이" type="number" ariaLabel="나이 수정" />
              <PillButton onClick={save} disabled={saving || !draft.age || Number(draft.age) <= 0}>{saving ? '저장 중...' : '저장'}</PillButton>
            </div>
          }
        >
          <FieldRow label="닉네임" value={data.nickname} />
          <FieldRow label="성별" value={genderLabel(data.gender)} />
          <FieldRow label="나이" value={data.age ? `${data.age}세` : ''} />
        </SectionCard>

        <SectionCard
          title="직업"
          editContent={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <BoxInput value={draft.occupation} onChange={v => setDraft(f => f && ({ ...f, occupation: v }))} placeholder="직업" ariaLabel="직업 수정" />
              <PillButton onClick={save} disabled={saving}>{saving ? '저장 중...' : '저장'}</PillButton>
            </div>
          }
        >
          <FieldRow label="직업" value={data.occupation} />
        </SectionCard>

        <SectionCard
          title="취미 · 관심사"
          editContent={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <div style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-sm)', color: 'var(--ink-meta)', marginBottom: 8 }}>취미</div>
                <TagInput
                  value={draft.hobbies}
                  onChange={v => setDraft(f => f && ({ ...f, hobbies: v }))}
                  placeholder="예: 독서"
                  ariaLabel="취미 수정"
                />
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-sm)', color: 'var(--ink-meta)', marginBottom: 8 }}>관심사</div>
                <TagInput
                  value={draft.interests}
                  onChange={v => setDraft(f => f && ({ ...f, interests: v }))}
                  placeholder="예: 건강"
                  ariaLabel="관심사 수정"
                />
              </div>
              <PillButton onClick={save} disabled={saving}>{saving ? '저장 중...' : '저장'}</PillButton>
            </div>
          }
        >
          <FieldRow label="취미" value={data.hobbies.join(', ')} />
          <FieldRow label="관심사" value={data.interests.join(', ')} />
        </SectionCard>

        <SectionCard
          title="알림"
          editContent={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <BoxInput value={draft.notification_time ?? ''} onChange={v => setDraft(f => f && ({ ...f, notification_time: v || null }))} type="time" ariaLabel="알림 시간 수정" />
              <PillButton onClick={save} disabled={saving}>{saving ? '저장 중...' : '저장'}</PillButton>
            </div>
          }
        >
          <FieldRow label="알림 시간" value={data.notification_time ?? '미설정'} />
          <div style={{ marginTop: 8 }}>
            {pushState === 'unsupported' ? (
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary, #888)' }}>이 브라우저는 푸시 알림을 지원하지 않습니다.</span>
            ) : pushState === 'denied' ? (
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary, #888)' }}>알림이 차단되었습니다. 브라우저 설정에서 허용해주세요.</span>
            ) : (
              <PillButton
                onClick={handlePushToggle}
                disabled={pushLoading}
              >
                {pushLoading ? '처리 중...' : pushState === 'subscribed' ? '알림 끄기' : '알림 켜기'}
              </PillButton>
            )}
          </div>
        </SectionCard>

        {/* 취향 섹션 */}
        <SectionCard title="취향">
          {tasteLoading ? (
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-sm)', color: 'var(--ink-hint)' }}>
              로딩 중...
            </span>
          ) : tasteProfile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {tasteProfile.music_genres.length > 0 && (
                <FieldRow label="음악 장르" value={tasteProfile.music_genres.join(', ')} />
              )}
              {tasteProfile.mbti && (
                <FieldRow label="MBTI" value={tasteProfile.mbti} />
              )}
              {tasteProfile.preferred_music_mood.length > 0 && (
                <FieldRow label="음악 분위기" value={tasteProfile.preferred_music_mood.join(', ')} />
              )}
              {tasteProfile.movie_genres.length > 0 && (
                <FieldRow label="좋아하는 장르" value={tasteProfile.movie_genres.join(', ')} />
              )}
              {tasteProfile.weekend_style && (
                <FieldRow label="주말 성향" value={tasteProfile.weekend_style} />
              )}
              <div style={{ marginTop: 8 }}>
                <PillButton onClick={() => navigate('/profile/taste')}>
                  취향 수정하기
                </PillButton>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-sm)', color: 'var(--ink-meta)' }}>
                아직 취향 문진을 작성하지 않았어요.
              </span>
              <PillButton onClick={() => navigate('/profile/taste')}>
                취향 문진 시작하기
              </PillButton>
            </div>
          )}
        </SectionCard>

        {!isStandalone && (
          <button
            onClick={async () => {
              if (canInstall) {
                const shown = await promptInstall()
                if (!shown) setGuideOpen(true)
              } else {
                setGuideOpen(true)
              }
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              padding: '12px 20px',
              borderRadius: 999,
              border: '1.5px solid var(--sage-leaf)',
              background: 'transparent',
              color: 'var(--sage-forest)',
              font: '500 15px/1 var(--font-sans)',
              cursor: 'pointer',
              letterSpacing: '0.005em',
              width: '100%',
              transition: 'background var(--dur-1) var(--ease-out)',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--sage-wash)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <Icon name="download" size={15} color="var(--sage-forest)" />
            앱으로 설치하기
          </button>
        )}
        <PillButton variant="danger" onClick={handleLogout}>로그아웃</PillButton>
      </div>
      <InstallGuideModal
        open={guideOpen}
        onClose={() => setGuideOpen(false)}
        mode={isIOSSafari ? 'ios-safari' : 'all'}
      />
    </div>
  )
}
