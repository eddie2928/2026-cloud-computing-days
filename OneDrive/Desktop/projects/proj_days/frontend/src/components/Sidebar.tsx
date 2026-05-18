import { NavLink } from 'react-router-dom'

export function Sidebar() {
  const linkStyle = ({ isActive }: { isActive: boolean }) => ({
    display: 'block',
    padding: '12px 16px',
    textDecoration: 'none',
    color: isActive ? '#4f46e5' : '#374151',
    fontWeight: isActive ? 600 : 400,
    background: isActive ? '#eef2ff' : 'transparent',
    borderRadius: 6,
  })

  return (
    <nav style={{
      width: 200,
      minHeight: '100vh',
      borderRight: '1px solid #e5e7eb',
      padding: '24px 12px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 24, padding: '0 4px' }}>
        AI 일기
      </div>
      <NavLink to="/qna" style={linkStyle}>QnA 작성</NavLink>
      <NavLink to="/calendar" style={linkStyle}>캘린더</NavLink>
      <NavLink to="/profile" style={linkStyle}>프로필</NavLink>
    </nav>
  )
}
