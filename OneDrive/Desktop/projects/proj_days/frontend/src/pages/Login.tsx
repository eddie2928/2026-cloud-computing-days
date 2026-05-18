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
      navigate('/qna')
    } catch {
      setError('비밀번호가 틀렸습니다.')
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
