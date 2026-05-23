import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Header } from '../components/layout/Header'
import { MoodPickerInline } from '../components/diary/MoodPickerInline'
import { DiaryBodyCard } from '../components/diary/DiaryBodyCard'
import { PillButton } from '../components/days/PillButton'
import { type Mood } from '../components/days/MoodEmoji'

interface DiaryData {
  date: string
  body: string
  emotion?: string
}

export function Diary() {
  const { date } = useParams<{ date: string }>()
  const navigate = useNavigate()
  const [diary, setDiary] = useState<DiaryData | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [shareToast, setShareToast] = useState('')

  useEffect(() => {
    if (!date) return
    client.get(`/diary/${date}`).then(res => {
      setDiary(res.data)
    }).catch(e => {
      if (e.response?.status === 404) setNotFound(true)
    })
  }, [date])

  const handleShare = async () => {
    if (!date) return
    try {
      const res = await client.post(`/diary/${date}/share`)
      const url = `${window.location.origin}${res.data.url}`
      try {
        await navigator.clipboard.writeText(url)
        setShareToast('링크가 복사되었어요!')
      } catch {
        window.prompt('링크를 복사하세요:', url)
      }
    } catch {
      setShareToast('공유 링크 생성에 실패했어요.')
    }
    setTimeout(() => setShareToast(''), 3000)
  }

  if (notFound) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Header title={date ?? ''} showBack />
        <div style={{ padding: 24, textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--ink-hint)' }}>
          아직 이 날의 일기가 없어요.
          <br /><br />
          <PillButton onClick={() => navigate(`/qna/${date}`)}>일기 작성하기</PillButton>
        </div>
      </div>
    )
  }

  if (!diary) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Header showBack />
        <div style={{ padding: 24, fontFamily: 'var(--font-sans)', color: 'var(--ink-hint)' }}>Loading...</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Header title={diary.date} showBack />
      <MoodPickerInline date={diary.date} initial={diary.emotion as Mood | undefined} />
      <div style={{ padding: '0 16px' }}>
        <DiaryBodyCard body={diary.body} />
      </div>
      {shareToast && (
        <div style={{
          position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--sage-ink)', color: '#fff', borderRadius: 20,
          padding: '8px 20px', fontFamily: 'var(--font-sans)', fontSize: 14,
          zIndex: 2000,
        }}>
          {shareToast}
        </div>
      )}
      <div style={{ padding: '8px 16px 16px', display: 'flex', gap: 12 }}>
        <PillButton variant="ghost" onClick={handleShare} style={{ flex: 1 }}>
          공유
        </PillButton>
      </div>
    </div>
  )
}
