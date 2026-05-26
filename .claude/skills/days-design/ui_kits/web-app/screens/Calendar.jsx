/* global window */
const { useState, Logo, Icon, SoftBackdrop } = window.DaysUI;

// Mood data shown in screenshot 2: May 2026
const MAY_2026_MOODS = {
  1:'happy', 2:'neutral',
  4:'sad', 5:'happy', 7:'angry', 8:'happy',
  10:'neutral', 11:'bored', 12:'happy', 13:'happy', 15:'sad', 16:'neutral',
  18:'happy', 19:'happy', 20:'bored', 22:'happy',
};
const EMOJI = { happy:'😊', sad:'😭', angry:'😠', neutral:'😐', bored:'😩' };
const WEEKDAYS = ['일','월','화','수','목','금','토'];

function CalendarScreen({ onOpenDiary, onCreateDiary, onProfile, today = 22, moods = MAY_2026_MOODS }) {
  // May 2026 starts on a Friday (index 5)
  const firstWeekday = 5;
  const daysInMonth = 31;
  const cells = [];
  for (let i = 0; i < firstWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div className="days-screen-fill" style={{
      position: 'relative',
      width: '100%', height: '100%',
      background: 'linear-gradient(180deg, var(--paper-bone) 0%, var(--sage-paper) 100%)',
      padding: '24px 24px 24px',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'auto',
      animation: 'days-fade-in 400ms var(--ease-out) both',
    }}>
      <SoftBackdrop variant="screen" />

      {/* Header */}
      <header style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 24,
        animation: 'days-rise 400ms var(--ease-out) 60ms both',
      }}>
        <Logo size={24} mark={true} markColor="var(--sage-forest)" color="var(--sage-ink)" />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={onProfile} aria-label="에디 프로필" style={{
            display: 'flex', alignItems: 'center', gap: 8,
            border: 0, background: 'transparent', cursor: 'pointer', padding: 0,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'var(--sage-leaf)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--paper-pure)',
            }}>
              <Icon name="user" size={18} color="var(--paper-pure)" />
            </div>
            <span className="t-label" style={{ fontSize: 'var(--t-base)', color: 'var(--ink-deep)' }}>에디</span>
          </button>
          <button aria-label="설정" style={{
            background: 'transparent', border: 0, cursor: 'pointer', padding: 6,
          }}>
            <Icon name="settings" size={22} color="var(--ink-body)" />
          </button>
        </div>
      </header>

      {/* Month navigator */}
      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 18,
        animation: 'days-rise 400ms var(--ease-out) 120ms both',
      }}>
        <button aria-label="이전 달" style={iconBtn}><Icon name="chevron-left" size={20} color="var(--ink-meta)" /></button>
        <div className="t-h1" style={{ fontSize: 'var(--t-xl)', whiteSpace: 'nowrap' }}>2026년 5월</div>
        <button aria-label="다음 달" style={iconBtn}><Icon name="chevron-right" size={20} color="var(--ink-meta)" /></button>
      </div>

      {/* Weekday header */}
      <div style={{
        position: 'relative',
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 4,
        marginBottom: 8,
        animation: 'days-fade-in 400ms var(--ease-out) 180ms both',
      }}>
        {WEEKDAYS.map(w => (
          <div key={w} style={{
            textAlign: 'center',
            fontFamily: 'var(--font-sans)',
            fontWeight: 500,
            fontSize: 'var(--t-sm)',
            color: 'var(--cal-weekday-label)',
            padding: '6px 0',
          }}>{w}</div>
        ))}
      </div>

      {/* Day cells */}
      <div style={{
        position: 'relative',
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 4,
      }}>
        {cells.map((day, i) => {
          if (day == null) return <div key={i} />;
          const mood = moods[day];
          const isToday = day === today;
          const hasEntry = !!mood;
          return (
            <button
              key={i}
              onClick={() => hasEntry ? onOpenDiary(day) : onCreateDiary(day)}
              style={{
                position: 'relative',
                aspectRatio: '1 / 1.2',
                padding: '6px 4px 4px',
                background: hasEntry ? 'var(--cal-day-bg)' : 'transparent',
                border: isToday ? '2px solid var(--cal-today-ring)' : '0',
                borderRadius: 'var(--r-4)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'flex-start',
                gap: 2,
                cursor: 'pointer',
                boxShadow: hasEntry ? 'var(--shadow-1)' : 'none',
                fontFamily: 'var(--font-sans)',
                fontSize: 'var(--t-sm)',
                color: 'var(--ink-meta)',
                transition: 'background var(--dur-1), transform var(--dur-1)',
                animation: `days-pop 400ms var(--ease-soft) ${200 + i * 8}ms both`,
              }}
            >
              <span style={{
                fontWeight: 500,
                color: isToday ? 'var(--sage-forest)' : 'var(--ink-body)',
              }}>{day}</span>
              {mood && <span style={{ fontSize: 18, lineHeight: 1 }}>{EMOJI[mood]}</span>}
            </button>
          );
        })}
      </div>

      <div style={{ flex: 1 }} />
    </div>
  );
}

const iconBtn = {
  background: 'transparent',
  border: 0,
  cursor: 'pointer',
  padding: 8,
  borderRadius: 'var(--r-pill)',
};

window.CalendarScreen = CalendarScreen;
window.MAY_2026_MOODS = MAY_2026_MOODS;
window.EMOJI = EMOJI;
