/* global window */
const { useState, PillButton, Icon, EMOJI } = window.DaysUI ? { ...window.DaysUI, EMOJI: window.EMOJI } : {};

const MOODS = ['happy','sad','angry','neutral','bored'];
const MOOD_LABEL = { happy:'행복', sad:'슬픔', angry:'화남', neutral:'보통', bored:'지루함' };

function DiaryDetailModal({ date = '5월 22일 (목)', initialEmoji = 'happy', initialBody, onClose, onSave }) {
  const [emoji, setEmoji] = useState(initialEmoji);
  const [body, setBody] = useState(
    initialBody ?? '오늘은 유난히 평온한 하루였다. 오후에 잠깐 산책을 나갔는데, 골목 끝에서 마주친 노을이 오래 기억에 남을 것 같다. 작은 풍경들이 사실 매일 곁에 있었구나 싶었다.'
  );

  return (
    <div style={{
      position: 'absolute', inset: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(46, 59, 31, 0.30)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      animation: 'days-fade-in 240ms var(--ease-out) both',
      padding: '0 18px',
      zIndex: 10,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 360,
        background: 'var(--paper-warm)',
        borderRadius: 'var(--r-6)',
        padding: '24px 22px 22px',
        boxShadow: 'var(--shadow-3)',
        animation: 'days-pop 380ms var(--ease-soft) both',
        position: 'relative',
      }}>
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div className="t-h3" style={{ fontWeight: 600 }}>{date}</div>
          <button onClick={onClose} aria-label="닫기" style={{
            background: 'transparent', border: 0, cursor: 'pointer', padding: 4,
          }}>
            <Icon name="close" size={22} color="var(--ink-meta)" />
          </button>
        </header>

        {/* Big mood emoji */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: 6, marginBottom: 14,
        }}>
          <div style={{
            width: 92, height: 92,
            borderRadius: '50%',
            background: 'var(--paper-pure)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 48,
            boxShadow: 'var(--shadow-2)',
          }}>{EMOJI[emoji]}</div>
          <div className="t-meta">{MOOD_LABEL[emoji]} · 탭하여 수정</div>
        </div>

        {/* Mood picker row */}
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 16,
        }}>
          {MOODS.map(m => (
            <button
              key={m}
              onClick={() => setEmoji(m)}
              style={{
                width: 40, height: 40,
                borderRadius: '50%',
                background: m === emoji ? 'var(--sage-cloud)' : 'transparent',
                border: m === emoji ? '1.5px solid var(--sage-leaf)' : '0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 22, cursor: 'pointer',
                transition: 'background var(--dur-1), border var(--dur-1)',
              }}
            >{EMOJI[m]}</button>
          ))}
        </div>

        {/* Diary body */}
        <div style={{
          background: 'var(--paper-pure)',
          borderRadius: 'var(--r-4)',
          padding: '14px 16px',
          marginBottom: 16,
          position: 'relative',
          boxShadow: 'var(--shadow-1)',
        }}>
          <div className="t-body-serif" style={{ fontSize: 'var(--t-base)', lineHeight: 1.75 }}>
            {body}
          </div>
          <span style={{
            position: 'absolute', top: 10, right: 10,
            display: 'inline-flex',
          }}>
            <Icon name="pencil" size={16} color="var(--ink-hint)" />
          </span>
        </div>

        <PillButton variant="primary" onClick={onSave}>저장</PillButton>
      </div>
    </div>
  );
}

window.DiaryDetailModal = DiaryDetailModal;
