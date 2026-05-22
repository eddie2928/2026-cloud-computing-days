import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { ProfileForm, type ProfileFormValue } from '../components/ProfileForm'

export function Profile() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [initial, setInitial] = useState<ProfileFormValue | null>(null)

  useEffect(() => {
    client.get('/profile').then((res) => {
      const d = res.data
      setInitial({
        nickname: d.nickname ?? '',
        gender: d.gender ?? '',
        age: d.age ?? '',
        occupation: d.occupation ?? '',
        hobbies: d.hobbies ?? [],
        interests: d.interests ?? [],
        notification_time: d.notification_time ?? null,
      })
    }).catch((e) => {
      if (e.response?.status === 404) {
        navigate('/onboarding', { replace: true })
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

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  if (!initial) return <div>Loading...</div>

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <button onClick={() => navigate('/')} style={{ padding: '6px 12px' }}>← 뒤로</button>
        <h2 style={{ margin: 0 }}>프로필 설정</h2>
        <button onClick={handleLogout} style={{ padding: '6px 12px' }}>로그아웃</button>
      </div>
      <ProfileForm initial={initial} submitLabel="저장" onSubmit={handleSubmit} />
    </div>
  )
}
