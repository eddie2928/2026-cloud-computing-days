import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Logo } from '../components/brand/Logo'

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
    <div
      style={{
        width: '100%',
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: '1.1fr 1fr',
        background: 'var(--paper-bone)',
      }}
    >
      {/* LEFT — brand panel */}
      <div
        style={{
          position: 'relative',
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(167,132,45,0.10) 1px, transparent 0), linear-gradient(160deg, var(--paper-cream) 0%, var(--paper-warm) 55%, var(--gold-mist) 100%)',
          backgroundSize: '20px 20px, 100% 100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '56px 56px 48px',
          overflow: 'hidden',
          borderRight: '1px solid var(--line-faint)',
        }}
      >
        <div style={{ position: 'relative', animation: 'days-rise 600ms var(--ease-out) 80ms both' }}>
          <Logo size={56} />
        </div>

        <div
          style={{
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            animation: 'days-rise 600ms var(--ease-out) 240ms both',
            maxWidth: 380,
          }}
        >
          <div
            style={{
              font: '500 11px/1 var(--font-sans)',
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: 'var(--gold-deep)',
            }}
          >
            daily diary · ai qna
          </div>
          <h1
            style={{
              margin: 0,
              font: '400 44px/1.2 var(--font-serif)',
              fontStyle: 'italic',
              color: 'var(--ink-coffee)',
              letterSpacing: '-0.015em',
            }}
          >
            오늘을 다섯 가지로,
            <br />
            가볍게.
          </h1>
          <div style={{ font: '400 16px/1.6 var(--font-sans)', color: 'var(--ink-bark)' }}>
            AI가 다섯 개의 질문을 던집니다.
            <br />
            떠오르는 대로 답하면, 하루가 한 페이지가 됩니다.
          </div>
        </div>

        <div
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            font: '400 12px/1 var(--font-sans)',
            color: 'var(--ink-stone)',
            letterSpacing: '0.04em',
          }}
        >
          <span style={{ width: 4, height: 4, borderRadius: 999, background: 'var(--gold-warm)' }} />
          <span>2026 · v0.1 · made with 인하대 NXT</span>
        </div>
      </div>

      {/* RIGHT — form */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 48,
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 420,
            background: 'var(--paper-cream)',
            border: '1px solid var(--line)',
            borderRadius: 24,
            padding: '40px 40px 32px',
            boxShadow: 'var(--shadow-3)',
            display: 'flex',
            flexDirection: 'column',
            gap: 24,
            animation: 'days-pop 500ms var(--ease-soft) both',
          }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              alignItems: 'flex-start',
              animation: 'days-rise 500ms var(--ease-out) 100ms both',
            }}
          >
            <Logo size={72} />
            <div style={{ font: '400 18px/1.5 var(--font-sans)', color: 'var(--ink-bark)' }}>
              하루를 다섯 가지로 정리해드릴게요.
            </div>
          </div>

          <hr style={{ border: 0, height: 1, background: 'var(--line-faint)', margin: 0 }} />

          <form
            onSubmit={handleSubmit}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
              animation: 'days-rise 500ms var(--ease-out) 220ms both',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <label
                htmlFor="password"
                style={{
                  font: '500 24px/1.1 var(--font-serif)',
                  fontStyle: 'italic',
                  color: 'var(--ink-coffee)',
                  letterSpacing: '-0.01em',
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
                  font: '400 16px/1.4 var(--font-sans)',
                  color: 'var(--ink-coffee)',
                  boxSizing: 'border-box',
                  padding: '10px 0',
                  background: 'transparent',
                  border: 0,
                  borderBottom: `1px solid ${pwFocused ? 'var(--gold-warm)' : 'var(--line)'}`,
                  borderRadius: 0,
                  outline: 'none',
                  transition: 'border-color 160ms var(--ease-out)',
                }}
              />
            </div>

            {error && (
              <div
                role="alert"
                style={{
                  font: '400 13px/1.4 var(--font-sans)',
                  color: 'var(--clay)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span style={{ width: 4, height: 4, borderRadius: 999, background: 'var(--clay)' }} />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={disabled}
              onMouseEnter={() => setBtnHover(true)}
              onMouseLeave={() => {
                setBtnHover(false)
                setBtnPress(false)
              }}
              onMouseDown={() => setBtnPress(true)}
              onMouseUp={() => setBtnPress(false)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '8px 18px 6px',
                borderRadius: 999,
                border: 0,
                background: disabled
                  ? 'var(--gold-soft)'
                  : btnHover
                  ? 'var(--gold)'
                  : 'var(--gold-warm)',
                color: 'var(--paper-bone)',
                font: '600 15px/1.4 var(--font-sans)',
                letterSpacing: '0.01em',
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.55 : 1,
                boxShadow: btnPress ? 'var(--shadow-press)' : 'var(--shadow-2)',
                transform: btnPress ? 'scale(0.98) translateY(1px)' : 'none',
                transition:
                  'background var(--dur-1) var(--ease-out), box-shadow var(--dur-1), transform var(--dur-1) var(--ease-soft)',
              }}
            >
              days와 하루를 정리하기
              <img
                src="/brand/icons/arrow-right.svg"
                width={16}
                height={16}
                alt=""
                style={{ filter: 'invert(1) brightness(1.5)' }}
              />
            </button>

            <div
              style={{
                font: '400 12px/1.4 var(--font-sans)',
                color: 'var(--ink-stone)',
                textAlign: 'center',
                marginTop: 4,
              }}
            >
              데모 비밀번호 ·{' '}
              <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--gold-deep)' }}>demo</code>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
