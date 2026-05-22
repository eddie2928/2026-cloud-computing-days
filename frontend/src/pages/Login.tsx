import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

export function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await client.post('/login', { password })
      try {
        await client.get('/profile')
        navigate('/')
      } catch (profileErr: unknown) {
        const profileStatus = (profileErr as { response?: { status?: number } })?.response?.status
        if (profileStatus === 404) {
          navigate('/onboarding')
        } else {
          throw profileErr
        }
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        setError('비밀번호가 틀렸습니다.')
      } else {
        setError('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.')
      }
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', padding: 24 }}>
      <h1>AI 일기 QnA</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ display: 'block', width: '100%', marginTop: 8, padding: 8 }}
          />
        </div>
        {error && <p role="alert" style={{ color: 'red' }}>{error}</p>}
        <button
          type="submit"
          disabled={!password}
          style={{ marginTop: 16, padding: '8px 24px' }}
        >
          로그인
        </button>
      </form>
    </div>
  )
}
