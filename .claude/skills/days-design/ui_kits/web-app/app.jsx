/* global window, React, ReactDOM */
const { useState, PhoneFrame } = window.DaysUI;

function App() {
  const [screen, setScreen] = useState('login');
  const [overlay, setOverlay] = useState(null);    // 'chat' | 'diary' | null
  const [chatDate, setChatDate] = useState(null);
  const [diaryDate, setDiaryDate] = useState(null);
  const [season, setSeason] = useState('spring');  // 'spring' | 'summer' | 'autumn' | 'winter'

  const go = (s) => { setScreen(s); setOverlay(null); };

  const labelOf = (s) => ({
    login: 'Login',
    onboarding: 'Onboarding',
    calendar: 'Calendar',
    profile: 'Profile',
  })[s];

  const seasonInfo = {
    spring: { label: '봄 · Spring',  range: '3 – 5월',  swatch: '#7D9D6A' },
    summer: { label: '여름 · Summer', range: '6 – 8월',  swatch: '#4FA3D6' },
    autumn: { label: '가을 · Autumn', range: '9 – 11월', swatch: '#D88444' },
    winter: { label: '겨울 · Winter', range: '12 – 2월', swatch: '#8194AB' },
  };

  const screenEl = (() => {
    switch (screen) {
      case 'login':
        return <window.LoginScreen onLogin={() => go('onboarding')} />;
      case 'onboarding':
        return <window.OnboardingScreen onComplete={() => go('calendar')} />;
      case 'calendar':
        return <window.CalendarScreen
          today={22}
          onProfile={() => go('profile')}
          onOpenDiary={(d) => { setDiaryDate(`5월 ${d}일`); setOverlay('diary'); }}
          onCreateDiary={(d) => { setChatDate(`5월 ${d}일`); setOverlay('chat'); }}
        />;
      case 'profile':
        return <window.ProfileScreen
          onBack={() => go('calendar')}
          onSave={() => go('calendar')}
          onLogout={() => go('login')}
        />;
      default:
        return null;
    }
  })();

  return (
    <div data-season={season} style={{
      width: '100%', minHeight: '100vh',
      background: `
        radial-gradient(ellipse 1200px 800px at 20% 110%, var(--sage-wash) 0%, transparent 55%),
        radial-gradient(ellipse 700px 500px at 90% -10%, var(--paper-warm) 0%, transparent 55%),
        var(--paper-bone)
      `,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '32px 16px 48px',
      gap: 20,
      transition: 'background var(--dur-3) var(--ease-out)',
    }}>
      {/* Top bar: app title + nav */}
      <header style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 6,
        marginTop: 8,
      }}>
        <window.Logo size={36} markColor="var(--sage-forest)" color="var(--sage-ink)" />
        <div className="t-meta">UI kit · click-through prototype</div>
      </header>

      {/* Season selector */}
      <div style={{
        display: 'flex',
        gap: 6,
        background: 'var(--paper-warm)',
        padding: 5,
        borderRadius: 'var(--r-pill)',
        boxShadow: 'var(--shadow-1)',
        flexWrap: 'wrap',
        justifyContent: 'center',
        maxWidth: '90vw',
      }}>
        {Object.entries(seasonInfo).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setSeason(k)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              borderRadius: 'var(--r-pill)',
              border: 0,
              background: season === k ? 'var(--sage-leaf)' : 'transparent',
              color: season === k ? 'var(--paper-pure)' : 'var(--ink-body)',
              fontFamily: 'var(--font-sans)',
              fontWeight: 500,
              fontSize: 'var(--t-sm)',
              cursor: 'pointer',
              transition: 'background var(--dur-2) var(--ease-out), color var(--dur-2)',
            }}
          >
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: v.swatch,
              boxShadow: season === k ? '0 0 0 2px var(--paper-pure)' : '0 0 0 1px rgba(0,0,0,0.05)',
            }} />
            {v.label}
            <span style={{ opacity: 0.6, fontSize: 'var(--t-xs)', marginLeft: 2 }}>{v.range}</span>
          </button>
        ))}
      </div>

      {/* Screen selector */}
      <nav style={{
        display: 'flex',
        gap: 6,
        background: 'var(--paper-warm)',
        padding: 5,
        borderRadius: 'var(--r-pill)',
        boxShadow: 'var(--shadow-1)',
        flexWrap: 'wrap',
        justifyContent: 'center',
        maxWidth: '90vw',
      }}>
        {['login','onboarding','calendar','profile'].map(s => (
          <button
            key={s}
            onClick={() => go(s)}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--r-pill)',
              border: 0,
              background: screen === s ? 'var(--sage-leaf)' : 'transparent',
              color: screen === s ? 'var(--paper-pure)' : 'var(--ink-body)',
              fontFamily: 'var(--font-sans)',
              fontWeight: 500,
              fontSize: 'var(--t-sm)',
              cursor: 'pointer',
              transition: 'background var(--dur-1)',
            }}
          >{labelOf(s)}</button>
        ))}
      </nav>

      <PhoneFrame label={labelOf(screen)}>
        <div data-screen-label={labelOf(screen)} style={{ position: 'relative', width: '100%', height: '100%' }}>
          {screenEl}
          {overlay === 'diary' && (
            <window.DiaryDetailModal
              date={`${diaryDate} (목)`}
              onClose={() => setOverlay(null)}
              onSave={() => setOverlay(null)}
            />
          )}
          {overlay === 'chat' && (
            <window.ChatScreen
              date={`${chatDate} (목)`}
              onClose={() => setOverlay(null)}
              onComplete={() => { setOverlay(null); }}
            />
          )}
        </div>
      </PhoneFrame>

      <footer className="t-caption" style={{ textAlign: 'center', maxWidth: 500, marginTop: 12, lineHeight: 1.5 }}>
        계절 토글 한 번이면 배경 · 버튼 · 채팅 버블 · 캘린더 today 링 · 포커스 링까지 전부 다시 칠해져요.
        Click a screen above. From <strong>Calendar</strong>, tap any day with an emoji to open the diary detail,
        or any empty day to start the 5-question AI chat.
      </footer>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
