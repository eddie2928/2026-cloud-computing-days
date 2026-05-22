/* global React, daysPrim */
const { useState: useStateProf } = React;

function ProfileScreen({ todayISO, savedDates }) {
  const [name, setName] = useStateProf('default-user');
  const [saved, setSaved] = useStateProf(false);
  const entries = savedDates.length;
  const firstISO = savedDates[0];

  return (
    <div style={{ width: '100%', maxWidth: 480, margin: '0 auto', padding: '48px 24px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, animation: 'days-rise 500ms var(--ease-out) 60ms both' }}>
        <daysPrim.Eyebrow>당신의 days</daysPrim.Eyebrow>
        <div style={{ font: '400 36px/1.1 var(--font-serif)', letterSpacing: '-0.015em', color: 'var(--ink-coffee)' }}>
          {name}
        </div>
      </div>

      <daysPrim.Card style={{ gap: 10, animation: 'days-rise 500ms var(--ease-out) 180ms both' }}>
        <daysPrim.Eyebrow style={{ color: 'var(--ink-bark)' }}>기록</daysPrim.Eyebrow>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ font: '400 15px/1.5 var(--font-sans)', color: 'var(--ink-bark)' }}>저장된 일기</span>
          <span style={{ font: '500 24px/1 var(--font-serif)', color: 'var(--ink-coffee)' }}>{entries}</span>
        </div>
        <hr style={{ border: 0, height: 1, background: 'var(--line-faint)', margin: '4px 0' }}/>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ font: '400 15px/1.5 var(--font-sans)', color: 'var(--ink-bark)' }}>처음 기록한 날</span>
          <span style={{ font: '500 14px/1 var(--font-mono)', color: 'var(--gold-deep)' }}>{firstISO || '—'}</span>
        </div>
      </daysPrim.Card>

      <form onSubmit={(e) => { e.preventDefault(); setSaved(true); setTimeout(() => setSaved(false), 1800); }}
        style={{ display: 'flex', flexDirection: 'column', gap: 14, animation: 'days-rise 500ms var(--ease-out) 320ms both' }}>
        <daysPrim.TextField label="표시 이름" value={name} onChange={setName}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <daysPrim.Button type="submit">저장</daysPrim.Button>
          {saved && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, font: '400 13px/1 var(--font-sans)', color: 'var(--sage)', animation: 'days-fade-in 240ms var(--ease-out) both' }}>
              <img src="../../assets/icons/check.svg" width="14" height="14"/> 저장됨
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

window.ProfileScreen = ProfileScreen;
