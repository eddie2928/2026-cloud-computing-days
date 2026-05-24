import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { CloudLeaf } from '../components/days/CloudLeaf'
import { Icon } from '../components/days/Icon'

export function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pwFocused, setPwFocused] = useState(false)
  const [btnHover, setBtnHover] = useState(false)
  const [btnPress, setBtnPress] = useState(false)
  const navigate = useNavigate()

  const disabled = !password

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await client.post('/login', { password })
      try {
        await client.get('/profile')
        navigate('/hub')
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
    <div
      style={{
        width: '100%',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        /* bg-clouds: 계절별 blob 그라데이션 */
        background: `
          radial-gradient(circle at 78% 22%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 18%),
          radial-gradient(ellipse 480px 320px at 18% 78%, var(--cloud-1) 0%, transparent 55%),
          radial-gradient(ellipse 360px 260px at 88% 88%, var(--cloud-2) 0%, transparent 55%),
          radial-gradient(ellipse 280px 220px at 12% 28%, var(--cloud-3) 0%, transparent 55%),
          linear-gradient(180deg, var(--paper-bone) 0%, var(--sage-wash) 100%)
        `,
        animation: 'days-fade-in 600ms var(--ease-out) both',
      }}
    >
      {/* 로고 + 워드마크 */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          marginBottom: 40,
          animation: 'days-rise 600ms var(--ease-out) 80ms both',
        }}
      >
        <div style={{ animation: 'days-drift 8s ease-in-out infinite' }}>
          <CloudLeaf size={72} color="var(--sage-forest)" stroke={2.4} />
        </div>
        <h1
          style={{
            margin: 0,
            fontFamily: 'var(--font-display)',
            fontWeight: 800,
            fontSize: 56,
            letterSpacing: '-0.04em',
            color: 'var(--sage-ink)',
            lineHeight: 1,
          }}
        >
          Days
        </h1>
        <p
          style={{
            margin: 0,
            font: '400 16px/1 var(--font-sans)',
            color: 'var(--ink-meta)',
            letterSpacing: '0.01em',
          }}
        >
          Your AI Diary
        </p>
      </div>

      {/* 폼 카드 */}
      <div
        style={{
          width: '100%',
          maxWidth: 400,
          background: 'var(--paper-pure)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          padding: '36px 36px 28px',
          boxShadow: 'var(--shadow-3)',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
          animation: 'days-pop 500ms var(--ease-soft) 160ms both',
        }}
      >
        <div
          style={{
            font: '600 18px/1.2 var(--font-sans)',
            color: 'var(--ink-deep)',
            letterSpacing: '-0.01em',
          }}
        >
          하루를 다섯 가지로 정리해요
        </div>

        <form
          onSubmit={handleSubmit}
          style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <label
              htmlFor="password"
              style={{
                font: '500 13px/1 var(--font-sans)',
                color: 'var(--ink-meta)',
                letterSpacing: '-0.005em',
              }}
            >
              비밀번호
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="•••••••••"
              autoFocus
              onFocus={() => setPwFocused(true)}
              onBlur={() => setPwFocused(false)}
              style={{
                padding: '12px 16px',
                borderRadius: 999,
                border: `1.5px solid ${pwFocused ? 'var(--sage-leaf)' : 'var(--line)'}`,
                background: 'var(--paper-bone)',
                font: '400 15px/1.4 var(--font-sans)',
                color: 'var(--ink-deep)',
                outline: 'none',
                boxShadow: pwFocused ? 'var(--shadow-ring)' : 'none',
                transition: 'border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out)',
              }}
            />
          </div>

          {error && (
            <div
              role="alert"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                font: '400 13px/1.4 var(--font-sans)',
                color: 'var(--accent-clay)',
              }}
            >
              <span
                style={{
                  width: 4,
                  height: 4,
                  borderRadius: 999,
                  background: 'var(--accent-clay)',
                  flexShrink: 0,
                }}
              />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={disabled}
            onMouseEnter={() => setBtnHover(true)}
            onMouseLeave={() => { setBtnHover(false); setBtnPress(false) }}
            onMouseDown={() => setBtnPress(true)}
            onMouseUp={() => setBtnPress(false)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              padding: '12px 20px',
              borderRadius: 999,
              border: 0,
              background: disabled
                ? 'var(--sage-mist)'
                : btnHover
                ? 'var(--sage-forest)'
                : 'var(--sage-leaf)',
              color: 'var(--paper-pure)',
              font: '600 15px/1 var(--font-sans)',
              letterSpacing: '0.01em',
              cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.6 : 1,
              boxShadow: disabled ? 'none' : btnPress ? 'var(--shadow-press)' : 'var(--shadow-2)',
              transform: btnPress ? 'scale(0.97) translateY(1px)' : 'none',
              transition: 'background var(--dur-1) var(--ease-out), box-shadow var(--dur-1), transform var(--dur-1) var(--ease-soft)',
            }}
          >
            시작하기
            <Icon name="arrow-right" size={16} color="var(--paper-pure)" />
          </button>
        </form>
      </div>
    </div>
  )
}
