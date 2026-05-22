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

  useEffect(() => {
    if (!date) return
    client.get(`/diary/${date}`).then(res => {
      setDiary(res.data)
    }).catch(e => {
      if (e.response?.status === 404) setNotFound(true)
    })
  }, [date])

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
      <div style={{ padding: '8px 16px 16px', display: 'flex', gap: 12 }}>
        <PillButton variant="ghost" onClick={() => navigate(`/qna/${date}`)} style={{ flex: 1 }}>
          다시 작성하기
        </PillButton>
        <PillButton variant="ghost" onClick={() => {}} style={{ flex: 1 }} disabled>
          공유
        </PillButton>
      </div>
    </div>
  )
}
