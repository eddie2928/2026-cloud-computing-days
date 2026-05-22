import { useState, type CSSProperties } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import client from '../api/client'
import { Logo } from './brand/Logo'

interface NavItem {
  to: string
  label: string
  icon: string
  match: (path: string) => boolean
}

const ITEMS: NavItem[] = [
  { to: '/', label: '오늘 쓰기', icon: 'pencil', match: (p) => p === '/' },
  { to: '/', label: '캘린더', icon: 'calendar', match: (p) => p === '/calendar' },
  { to: '/profile', label: '프로필', icon: 'user', match: (p) => p.startsWith('/profile') },
]

// Calendar shares the home route — collapse to two visible items.
const VISIBLE: NavItem[] = [
  { to: '/', label: '오늘 쓰기', icon: 'pencil', match: (p) => p === '/' },
  { to: '/profile', label: '프로필', icon: 'user', match: (p) => p.startsWith('/profile') },
]

export function Sidebar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [hovered, setHovered] = useState<string | null>(null)

  const logout = async () => {
    try {
      await client.post('/logout')
    } catch {
      // ignore
    }
    navigate('/login', { replace: true })
  }

  // Keep ITEMS reference to satisfy potential future use
  void ITEMS

  return (
    <nav
      style={{
        width: 220,
        minHeight: '100vh',
        background: 'var(--paper-cream)',
        borderRight: '1px solid var(--line)',
        padding: '24px 14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        flexShrink: 0,
        position: 'sticky',
        top: 0,
        animation: 'days-fade-in 400ms var(--ease-out) both',
      }}
    >
      <div
        style={{
          padding: '4px 8px 14px',
          borderBottom: '1px solid var(--line-faint)',
          marginBottom: 10,
        }}
      >
        <Logo size={36} />
      </div>

      {VISIBLE.map((it, i) => {
        const isActive = it.match(pathname)
        const isHover = hovered === it.label
        const style: CSSProperties = {
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '10px 12px',
          borderRadius: 10,
          border: 0,
          background: isActive ? 'var(--gold-mist)' : isHover ? 'var(--paper-mist)' : 'transparent',
          color: isActive ? 'var(--ink-coffee)' : 'var(--ink-bark)',
          font: '500 14px/1 var(--font-sans)',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background var(--dur-1) var(--ease-out), color var(--dur-1)',
          animation: `days-slide-in 380ms var(--ease-out) ${80 + i * 60}ms both`,
          position: 'relative',
        }
        return (
          <button
            key={it.label}
            onClick={() => navigate(it.to)}
            onMouseEnter={() => setHovered(it.label)}
            onMouseLeave={() => setHovered(null)}
            style={style}
          >
            {isActive && (
              <span
                style={{
                  position: 'absolute',
                  left: -4,
                  width: 4,
                  height: 4,
                  borderRadius: 999,
                  background: 'var(--gold-warm)',
                }}
              />
            )}
            <img
              src={`/brand/icons/${it.icon}.svg`}
              alt=""
              width={18}
              height={18}
              style={{ opacity: isActive ? 1 : 0.7 }}
            />
            {it.label}
          </button>
        )
      })}

      <div style={{ flex: 1 }} />
      <button
        onClick={logout}
        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--ink-coffee)')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--ink-stone)')}
        style={{
          background: 'transparent',
          border: 0,
          padding: '10px 12px',
          color: 'var(--ink-stone)',
          font: '400 12px/1 var(--font-sans)',
          textAlign: 'left',
          cursor: 'pointer',
          transition: 'color var(--dur-1)',
        }}
      >
        로그아웃
      </button>
    </nav>
  )
}
