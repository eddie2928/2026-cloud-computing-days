/* global React, daysPrim */
function DiaryDoneScreen({ date, diary, onToCalendar, onBackToToday }) {
  return (
    <div style={{ width: '100%', maxWidth: 600, margin: '0 auto', padding: '56px 24px 80px', display: 'flex', flexDirection: 'column', gap: 22 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start', animation: 'days-pop 500ms var(--ease-soft) both' }}>
        <span style={{
          width: 36, height: 36, borderRadius: 999,
          background: 'linear-gradient(180deg, var(--gold-warm), var(--gold))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 6px rgba(94,70,30,0.14)',
        }}>
          <img src="../../assets/icons/check.svg" width="20" height="20" style={{ filter: 'invert(1) brightness(2)' }}/>
        </span>
        <daysPrim.Eyebrow>{date}</daysPrim.Eyebrow>
        <div style={{ font: '400 36px/1.1 var(--font-serif)', letterSpacing: '-0.015em', color: 'var(--ink-coffee)' }}>
          오늘이 저장되었어요.
        </div>
      </div>

      <div style={{
        background: 'var(--paper-cream)',
        border: '1px solid var(--line)',
        borderRadius: 18,
        padding: '26px 28px',
        boxShadow: '0 2px 6px rgba(94,70,30,0.08)',
        animation: 'days-rise 600ms var(--ease-out) 180ms both',
      }}>
        <div style={{ font: '400 16px/1.78 var(--font-serif)', color: 'var(--ink-walnut)', whiteSpace: 'pre-wrap' }}>{diary}</div>
      </div>

      <div style={{ display: 'flex', gap: 12, animation: 'days-fade-in 500ms var(--ease-out) 420ms both' }}>
        <daysPrim.Button onClick={onToCalendar}>캘린더에서 보기</daysPrim.Button>
        <daysPrim.Button variant="secondary" onClick={onBackToToday}>처음으로</daysPrim.Button>
      </div>
    </div>
  );
}

window.DiaryDoneScreen = DiaryDoneScreen;
