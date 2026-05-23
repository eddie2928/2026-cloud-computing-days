import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import client from '../api/client'
import { Header } from '../components/layout/Header'
import { DiaryBodyCard } from '../components/diary/DiaryBodyCard'

interface SharedDiary {
  date: string
  body: string
  emotion: string
}

export function Share() {
  const { token } = useParams<{ token: string }>()
  const [diary, setDiary] = useState<SharedDiary | null>(null)
  const [error, setError] = useState<'expired' | 'notfound' | null>(null)

  useEffect(() => {
    if (!token) return
    client.get(`/share/${token}`).then(res => {
      setDiary(res.data)
    }).catch(e => {
      if (e.response?.status === 410) setError('expired')
      else setError('notfound')
    })
  }, [token])

  if (error === 'expired') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Header title="공유 일기" showBack />
        <div style={{ padding: 24, textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--ink-hint)' }}>
          링크가 만료되었어요.
        </div>
      </div>
    )
  }

  if (error === 'notfound') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Header title="공유 일기" showBack />
        <div style={{ padding: 24, textAlign: 'center', fontFamily: 'var(--font-sans)', color: 'var(--ink-hint)' }}>
          존재하지 않는 링크예요.
        </div>
      </div>
    )
  }

  if (!diary) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Header title="공유 일기" showBack />
        <div style={{ padding: 24, fontFamily: 'var(--font-sans)', color: 'var(--ink-hint)' }}>Loading...</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Header title={diary.date} showBack />
      <div style={{ padding: '0 16px' }}>
        <DiaryBodyCard body={diary.body} />
      </div>
    </div>
  )
}
