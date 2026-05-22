/* global React */
const { useMemo } = React;

function CalendarMonth({ year, month /* 1..12 */, savedDates, todayISO, onPickDate }) {
  const days = useMemo(() => {
    const first = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0).getDate();
    const startDow = first.getDay(); // 0 Sun
    const cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= lastDay; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  }, [year, month]);

  const monthName = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'][month - 1];
  const iso = (d) => `${year}-${String(month).padStart(2,'0')}-${String(d).padStart(2,'0')}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, animation: 'days-rise 500ms var(--ease-out) both' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div style={{ font: '400 28px/1.2 var(--font-serif)', color: 'var(--ink-coffee)', letterSpacing: '-0.01em' }}>{year}년 {monthName}</div>
        <div style={{ font: '500 12px/1 var(--font-mono)', color: 'var(--ink-stone)' }}>
          {savedDates.filter(d => d.startsWith(`${year}-${String(month).padStart(2,'0')}`)).length} entries
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {['일','월','화','수','목','금','토'].map((d, i) => (
          <div key={d} style={{ font: '500 11px/1 var(--font-mono)', color: i === 0 ? 'var(--clay)' : 'var(--ink-stone)', textAlign: 'center', padding: '8px 0', letterSpacing: '0.06em' }}>{d}</div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 6 }}>
        {days.map((d, i) => {
          if (d === null) return <div key={i}/>;
          const dateISO = iso(d);
          const isSaved = savedDates.includes(dateISO);
          const isToday = dateISO === todayISO;
          const isFuture = dateISO > todayISO;
          const dow = (i % 7);
          const colorNum = isToday ? 'var(--ink-coffee)' : isSaved ? 'var(--ink-coffee)' : isFuture ? 'var(--ink-soft)' : (dow === 0 ? 'var(--clay)' : 'var(--ink-bark)');
          return (
            <button
              key={i}
              disabled={!isSaved && !isToday}
              onClick={() => (isSaved || isToday) && onPickDate(dateISO, isSaved)}
              style={{
                aspectRatio: '1',
                background: isToday ? 'var(--gold-mist)' : isSaved ? 'var(--paper-cream)' : 'var(--paper-mist)',
                border: isToday ? '1.5px solid var(--gold)' : '1px solid var(--line-faint)',
                borderRadius: 10,
                padding: '8px 9px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                cursor: (isSaved || isToday) ? 'pointer' : 'default',
                font: '500 13px/1 var(--font-mono)',
                color: colorNum,
                transition: 'background var(--dur-1), transform var(--dur-1)',
                animation: `days-pop 380ms var(--ease-soft) ${30 + (i % 7) * 10 + Math.floor(i/7) * 20}ms both`,
              }}
              onMouseEnter={(e) => { if (isSaved || isToday) e.currentTarget.style.background = 'var(--gold-glow)'; }}
              onMouseLeave={(e) => { if (isSaved || isToday) e.currentTarget.style.background = isToday ? 'var(--gold-mist)' : 'var(--paper-cream)'; }}
            >
              <span>{d}</span>
              {isSaved && (
                <span style={{
                  width: 8, height: 8, borderRadius: 999,
                  background: 'var(--gold-warm)',
                  boxShadow: '0 1px 2px rgba(94,70,30,0.18)',
                  alignSelf: 'flex-end',
                }}/>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

window.CalendarMonth = CalendarMonth;
