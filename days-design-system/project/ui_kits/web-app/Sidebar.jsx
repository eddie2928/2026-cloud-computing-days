/* global React, Logo */
function Sidebar({ active, onNavigate, onLogout }) {
  const items = [
    { id: 'today',    label: '오늘 쓰기', icon: 'pencil' },
    { id: 'calendar', label: '캘린더',    icon: 'calendar' },
    { id: 'profile',  label: '프로필',    icon: 'user' },
  ];

  return (
    <nav style={{
      width: 220,
      minHeight: '100%',
      background: 'var(--paper-cream)',
      borderRight: '1px solid var(--line)',
      padding: '24px 14px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      flexShrink: 0,
      animation: 'days-fade-in 400ms var(--ease-out) both',
    }}>
      <div style={{ padding: '2px 6px 12px', borderBottom: '1px solid var(--line-faint)', marginBottom: 10 }}>
        <Logo size={36}/>
      </div>
      {items.map((it, i) => {
        const isActive = it.id === active;
        return (
          <button
            key={it.id}
            onClick={() => onNavigate(it.id)}
            onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--paper-mist)'; }}
            onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px',
              borderRadius: 10,
              border: 0,
              background: isActive ? 'var(--gold-mist)' : 'transparent',
              color: isActive ? 'var(--ink-coffee)' : 'var(--ink-bark)',
              font: '500 14px/1 var(--font-sans)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background var(--dur-1) var(--ease-out)',
              animation: `days-slide-in 380ms var(--ease-out) ${80 + i * 60}ms both`,
              position: 'relative',
            }}>
            {isActive && (
              <span style={{ position: 'absolute', left: -4, width: 4, height: 4, borderRadius: 999, background: 'var(--gold-warm)' }}/>
            )}
            <img src={`../../assets/icons/${it.icon}.svg`} alt="" width={18} height={18} style={{ opacity: isActive ? 1 : 0.7 }}/>
            {it.label}
          </button>
        );
      })}

      <div style={{ flex: 1 }}/>
      <button
        onClick={onLogout}
        onMouseEnter={(e) => e.currentTarget.style.color = 'var(--ink-coffee)'}
        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--ink-stone)'}
        style={{
          background: 'transparent', border: 0, padding: '10px 12px',
          color: 'var(--ink-stone)',
          font: '400 12px/1 var(--font-sans)',
          textAlign: 'left',
          cursor: 'pointer',
          transition: 'color var(--dur-1)',
        }}>
        로그아웃
      </button>
    </nav>
  );
}

window.Sidebar = Sidebar;
