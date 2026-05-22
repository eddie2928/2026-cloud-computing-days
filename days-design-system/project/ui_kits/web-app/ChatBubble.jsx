/* global React, daysPrim */
function ChatBubble({ role, children, animateDelay = 0 }) {
  const isAi = role === 'ai';
  return (
    <div style={{
      display: 'flex',
      gap: 10,
      alignItems: 'flex-start',
      justifyContent: isAi ? 'flex-start' : 'flex-end',
      animation: `days-rise 420ms var(--ease-out) ${animateDelay}ms both`,
    }}>
      {isAi && (
        <div style={{
          width: 32, height: 32, borderRadius: 999,
          background: 'var(--paper-warm)',
          border: '1px solid var(--line)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
          overflow: 'hidden',
        }}>
          <img src="../../assets/daisy-white.svg" alt="" style={{ width: 22, height: 22, display: 'block', animation: 'days-daisy-spin 9s var(--ease-out) infinite', transformOrigin: '50% 50%' }}/>
        </div>
      )}
      <div style={{
        maxWidth: '72%',
        padding: '12px 16px',
        font: '400 15px/1.55 var(--font-sans)',
        color: 'var(--ink-coffee)',
        background: isAi ? 'var(--bubble-ai)' : 'var(--bubble-user)',
        border: isAi ? 'none' : '1px solid var(--bubble-border)',
        borderRadius: isAi ? '4px 18px 18px 18px' : '18px 4px 18px 18px',
        whiteSpace: 'pre-wrap',
      }}>{children}</div>
    </div>
  );
}

function ThinkingBubble() {
  return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', animation: 'days-fade-in 240ms var(--ease-out) both' }}>
      <div style={{
        width: 32, height: 32, borderRadius: 999,
        background: 'var(--paper-warm)',
        border: '1px solid var(--line)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        overflow: 'hidden',
      }}>
        <img src="../../assets/daisy-white.svg" alt="" style={{ width: 22, height: 22, display: 'block', animation: 'days-daisy-spin 9s var(--ease-out) infinite', transformOrigin: '50% 50%' }}/>
      </div>
      <div style={{
        padding: '14px 18px',
        background: 'var(--bubble-ai)',
        borderRadius: '4px 18px 18px 18px',
      }}><daysPrim.ThinkingDots/></div>
    </div>
  );
}

window.ChatBubble = ChatBubble;
window.ThinkingBubble = ThinkingBubble;
