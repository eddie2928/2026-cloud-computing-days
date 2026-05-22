/* global React, daysPrim */
const { useState: useStateToday } = React;

function TodayScreen({ todayISO, savedDates, onBegin, onResume }) {
  const [date, setDate] = useStateToday(todayISO);
  const alreadySaved = savedDates.includes(date);

  return (
    <div style={{ width: '100%', maxWidth: 560, margin: '0 auto', padding: '64px 24px 80px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, animation: 'days-rise 500ms var(--ease-out) 60ms both' }}>
        <daysPrim.Eyebrow>오늘 · {todayISO.replace(/-/g, ' · ')}</daysPrim.Eyebrow>
        <div style={{ font: '400 40px/1.1 var(--font-serif)', letterSpacing: '-0.015em', color: 'var(--ink-coffee)' }}>
          오늘은 어떤 하루였나요?
        </div>
        <div style={{ font: '400 15px/1.6 var(--font-sans)', color: 'var(--ink-bark)', maxWidth: 440 }}>
          다섯 가지를 물어봐 드릴게요. 떠오르는 대로 답하시면 일기로 정리해드려요. 3분이면 충분합니다.
        </div>
      </div>

      <daysPrim.Card style={{ padding: '22px 24px', animation: 'days-rise 500ms var(--ease-out) 200ms both' }}>
        <daysPrim.Eyebrow>날짜 선택</daysPrim.Eyebrow>
        <daysPrim.DateField value={date} onChange={setDate}/>
        {alreadySaved ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, font: '400 13px/1.4 var(--font-sans)', color: 'var(--sage)' }}>
            <img src="../../assets/icons/check.svg" width="16" height="16"/>
            이 날의 일기는 이미 저장되어 있어요.
          </div>
        ) : (
          <div style={{ font: '400 12px/1.4 var(--font-sans)', color: 'var(--ink-stone)' }}>
            과거 날짜도 선택할 수 있어요. 미래 날짜는 비활성화됩니다.
          </div>
        )}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 4 }}>
          {alreadySaved ? (
            <daysPrim.Button variant="secondary" onClick={() => onResume(date)}>일기 보기</daysPrim.Button>
          ) : (
            <daysPrim.Button onClick={() => onBegin(date)}>
              시작 <img src="../../assets/icons/arrow-right.svg" width="16" height="16" style={{ filter: 'invert(1) brightness(1.5)' }}/>
            </daysPrim.Button>
          )}
        </div>
      </daysPrim.Card>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '8px 4px', animation: 'days-rise 500ms var(--ease-out) 340ms both' }}>
        <daysPrim.Eyebrow style={{ color: 'var(--ink-stone)' }}>최근</daysPrim.Eyebrow>
        {savedDates.slice(-3).reverse().map((d, i) => (
          <button key={d}
            onClick={() => onResume(d)}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--paper-mist)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            style={{
              display: 'flex', alignItems: 'center', gap: 12,
              background: 'transparent', border: 0, borderBottom: '1px solid var(--line-faint)',
              padding: '12px 6px',
              cursor: 'pointer',
              transition: 'background var(--dur-1)',
              textAlign: 'left',
              animation: `days-fade-in 400ms var(--ease-out) ${400 + i * 80}ms both`,
            }}>
            <span style={{ width: 8, height: 8, borderRadius: 999, background: 'var(--gold-warm)', flexShrink: 0 }}/>
            <span style={{ font: '500 14px/1 var(--font-mono)', color: 'var(--ink-walnut)', minWidth: 110 }}>{d}</span>
            <daysPrim.DotLeader/>
            <span style={{ font: '400 13px/1.4 var(--font-sans)', color: 'var(--ink-stone)' }}>일기 보기</span>
            <img src="../../assets/icons/arrow-right.svg" width="14" height="14" style={{ opacity: 0.5 }}/>
          </button>
        ))}
      </div>
    </div>
  );
}

window.TodayScreen = TodayScreen;
