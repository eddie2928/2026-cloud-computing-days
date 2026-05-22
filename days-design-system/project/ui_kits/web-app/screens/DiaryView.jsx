/* global React, daysPrim */
function DiaryViewScreen({ date, diary, onBack }) {
  if (!diary) {
    return (
      <div style={{ width: '100%', maxWidth: 600, margin: '0 auto', padding: '64px 24px', display: 'flex', flexDirection: 'column', gap: 18 }}>
        <daysPrim.Button variant="ghost" onClick={onBack} style={{ alignSelf: 'flex-start' }}>← 돌아가기</daysPrim.Button>
        <div style={{ font: '400 28px/1.2 var(--font-serif)', color: 'var(--ink-stone)' }}>{date}</div>
        <div style={{ font: '400 15px/1.6 var(--font-sans)', color: 'var(--ink-bark)' }}>이 날의 일기는 아직 없어요.</div>
      </div>
    );
  }

  // Parse YYYY-MM-DD into display
  const [y, m, d] = date.split('-').map(Number);
  const weekday = ['일','월','화','수','목','금','토'][new Date(y, m - 1, d).getDay()];

  return (
    <div style={{ width: '100%', maxWidth: 600, margin: '0 auto', padding: '48px 24px 80px', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <daysPrim.Button variant="ghost" onClick={onBack} style={{ alignSelf: 'flex-start', animation: 'days-fade-in 300ms var(--ease-out) both' }}>← 캘린더</daysPrim.Button>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, animation: 'days-rise 500ms var(--ease-out) 80ms both' }}>
        <daysPrim.Eyebrow>{y}년</daysPrim.Eyebrow>
        <div style={{ font: '400 36px/1.1 var(--font-serif)', letterSpacing: '-0.015em', color: 'var(--ink-coffee)' }}>
          {m}월 {d}일, {weekday}요일
        </div>
      </div>

      <div style={{
        background: 'var(--paper-cream)',
        border: '1px solid var(--line)',
        borderRadius: 18,
        padding: '28px 30px',
        boxShadow: '0 2px 6px rgba(94,70,30,0.08)',
        animation: 'days-rise 500ms var(--ease-out) 200ms both',
      }}>
        <div style={{ font: '400 16px/1.78 var(--font-serif)', color: 'var(--ink-walnut)', whiteSpace: 'pre-wrap' }}>{diary}</div>
      </div>

      <div style={{ display: 'flex', gap: 14, justifyContent: 'flex-end', paddingTop: 4, font: '400 12px/1 var(--font-mono)', color: 'var(--ink-stone)', animation: 'days-fade-in 400ms var(--ease-out) 400ms both' }}>
        <span>5 questions · 1 entry</span>
      </div>
    </div>
  );
}

window.DiaryViewScreen = DiaryViewScreen;
