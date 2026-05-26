/* global window */
const { useState, Logo, CloudLeaf, PillButton, PillInput, BoxInput, Icon, SoftBackdrop } = window.DaysUI;

function GoogleG({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.48h4.84c-.21 1.13-.84 2.09-1.79 2.73v2.27h2.9c1.7-1.56 2.69-3.87 2.69-6.64z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.9-2.27c-.81.54-1.83.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.94v2.34A9 9 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.16.29-1.7V4.96H.94A9 9 0 0 0 0 9c0 1.45.35 2.83.94 4.04l3.01-2.34z"/>
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58A9 9 0 0 0 9 0 9 9 0 0 0 .94 4.96l3.01 2.34C4.66 5.17 6.65 3.58 9 3.58z"/>
    </svg>
  );
}

function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('••••••••');
  const canSubmit = email.length > 0 && password.length > 0;

  return (
    <div className="bg-clouds days-screen-fill" style={{
      position: 'relative',
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: '64px 32px 40px',
      animation: 'days-fade-in 600ms var(--ease-out) both',
    }}>
      <SoftBackdrop variant="login" />

      {/* Logo + wordmark */}
      <div style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
        marginBottom: 36,
        animation: 'days-rise 600ms var(--ease-out) 80ms both',
      }}>
        <CloudLeaf size={64} color="var(--sage-forest)" stroke={2.4} />
        <h1 className="t-wordmark" style={{ margin: 0, fontSize: 56, letterSpacing: '-0.04em' }}>Days</h1>
        <div className="t-body" style={{ color: 'var(--ink-meta)', fontSize: 'var(--t-md)' }}>Your AI Diary</div>
      </div>

      {/* Form */}
      <div style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        animation: 'days-rise 600ms var(--ease-out) 220ms both',
      }}>
        <PillInput
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          icon={<Icon name="user" size={16} color="var(--ink-meta)" />}
          ariaLabel="Email"
        />
        <PillInput
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          icon={<Icon name="lock" size={16} color="var(--ink-meta)" />}
          ariaLabel="Password"
        />
      </div>

      <div style={{ marginTop: 16, animation: 'days-rise 600ms var(--ease-out) 320ms both' }}>
        <PillButton variant="primary" onClick={() => canSubmit && onLogin()} disabled={!canSubmit}>
          Log In
        </PillButton>
      </div>

      <button style={{
        margin: '12px auto 0',
        background: 'transparent',
        border: 0,
        color: 'var(--sage-forest)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--t-sm)',
        fontWeight: 500,
        cursor: 'pointer',
        animation: 'days-fade-in 600ms var(--ease-out) 380ms both',
      }}>
        Forgot password?
      </button>

      {/* OR separator */}
      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        margin: '14px 0',
        color: 'var(--ink-meta)',
        fontSize: 'var(--t-sm)',
        animation: 'days-fade-in 600ms var(--ease-out) 440ms both',
      }}>
        <div style={{ flex: 1, height: 1, background: 'var(--line)' }} />
        <span style={{ fontSize: 'var(--t-xs)' }}>or</span>
        <div style={{ flex: 1, height: 1, background: 'var(--line)' }} />
      </div>

      {/* Google sign in */}
      <div style={{ position: 'relative', animation: 'days-rise 600ms var(--ease-out) 520ms both' }}>
        <PillButton variant="ghost" icon={<GoogleG size={18} />} onClick={onLogin}>
          Continue with Google
        </PillButton>
      </div>
    </div>
  );
}

window.LoginScreen = LoginScreen;
