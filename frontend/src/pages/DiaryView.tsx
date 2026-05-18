import { useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import client from '../api/client'

export function DiaryView() {
  const { date } = useParams<{ date: string }>()
  const [body, setBody] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!date) return
    client.get(`/diary/${date}`)
      .then((r) => setBody(r.data.body))
      .catch((e) => {
        if (e.response?.status === 404) setNotFound(true)
      })
  }, [date])

  if (notFound) return <div style={{ padding: 24 }}><p>{date}에 일기가 없습니다.</p></div>
  if (!body) return <div style={{ padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2>{date} 일기</h2>
      <div style={{
        background: '#f9fafb',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: 16,
        whiteSpace: 'pre-wrap',
      }}>
        {body}
      </div>
    </div>
  )
}
