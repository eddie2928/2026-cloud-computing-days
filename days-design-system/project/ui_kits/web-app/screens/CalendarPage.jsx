/* global React, CalendarMonth, daysPrim */
const { useState: useStateCal } = React;

function CalendarScreen({ todayISO, savedDates, onPickDate }) {
  const [d] = useStateCal(new Date(todayISO));
  const [yr, setYr] = useStateCal(d.getFullYear());
  const [mo, setMo] = useStateCal(d.getMonth() + 1);

  const shift = (delta) => {
    let nm = mo + delta;
    let ny = yr;
    if (nm < 1) { nm = 12; ny -= 1; }
    if (nm > 12) { nm = 1; ny += 1; }
    setMo(nm); setYr(ny);
  };

  return (
    <div style={{ width: '100%', maxWidth: 720, margin: '0 auto', padding: '40px 24px 80px', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', animation: 'days-fade-in 400ms var(--ease-out) both' }}>
        <daysPrim.Eyebrow>지난 날</daysPrim.Eyebrow>
        <div style={{ display: 'flex', gap: 4 }}>
          <button onClick={() => shift(-1)}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--paper-mist)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            style={{ border: '1px solid var(--line)', background: 'transparent', padding: '6px 10px', borderRadius: 10, cursor: 'pointer', transition: 'background var(--dur-1)' }}>
            <img src="../../assets/icons/arrow-right.svg" width="14" height="14" style={{ transform: 'rotate(180deg)' }}/>
          </button>
          <button onClick={() => shift(1)}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--paper-mist)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            style={{ border: '1px solid var(--line)', background: 'transparent', padding: '6px 10px', borderRadius: 10, cursor: 'pointer', transition: 'background var(--dur-1)' }}>
            <img src="../../assets/icons/arrow-right.svg" width="14" height="14"/>
          </button>
        </div>
      </div>

      <CalendarMonth
        key={`${yr}-${mo}`}
        year={yr}
        month={mo}
        savedDates={savedDates}
        todayISO={todayISO}
        onPickDate={onPickDate}
      />

      <div style={{ display: 'flex', gap: 18, alignItems: 'center', paddingTop: 8, font: '400 12px/1.4 var(--font-sans)', color: 'var(--ink-stone)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: 'var(--gold-warm)' }}/> 저장됨
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 4, background: 'var(--gold-mist)', border: '1.5px solid var(--gold)' }}/> 오늘
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 10, height: 10, borderRadius: 4, background: 'var(--paper-mist)', border: '1px solid var(--line-faint)' }}/> 비어있음
        </span>
      </div>
    </div>
  );
}

window.CalendarScreen = CalendarScreen;
