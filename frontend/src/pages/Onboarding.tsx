import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { ProfileForm, type ProfileFormValue } from '../components/ProfileForm'

const EMPTY: ProfileFormValue = {
  nickname: '',
  gender: '',
  age: '',
  occupation: '',
  hobbies: [],
  interests: [],
  notification_time: null,
}

export function Onboarding() {
  const navigate = useNavigate()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    client.get('/profile').then(() => {
      navigate('/', { replace: true })
    }).catch((e) => {
      if (e.response?.status === 404) {
        setReady(true)
      }
    })
  }, [navigate])

  const handleSubmit = async (v: ProfileFormValue) => {
    await client.put('/profile', {
      ...v,
      age: Number(v.age),
      notification_time: v.notification_time ?? null,
    })
    navigate('/')
  }

  if (!ready) return <div>Loading...</div>

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', padding: 24 }}>
      <h1>프로필 설정</h1>
      <p>AI 맞춤형 질문 생성을 위한 기초 정보를 입력해 주세요.</p>
      <ProfileForm initial={EMPTY} submitLabel="시작하기" onSubmit={handleSubmit} />
    </div>
  )
}
