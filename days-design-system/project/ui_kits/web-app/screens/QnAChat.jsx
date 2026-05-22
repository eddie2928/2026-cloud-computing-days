/* global React, ChatBubble, ThinkingBubble, daysPrim */
const { useState: useStateQnA, useEffect: useEffectQnA, useRef: useRefQnA } = React;

const QUESTIONS = [
  '오늘 가장 기억에 남는 순간은 무엇이었나요?',
  '그때 어떤 기분이었어요?',
  '오늘 하루 중 가장 고마웠던 사람은 누구인가요?',
  '내일의 나에게 한 가지를 남긴다면 어떤 말일까요?',
  '오늘 하루를 한 문장으로 표현해본다면요?',
];

function QnAChatScreen({ date, onComplete, onCancel }) {
  const [messages, setMessages] = useStateQnA([{ role: 'ai', text: QUESTIONS[0], seq: 1 }]);
  const [seq, setSeq] = useStateQnA(1);
  const [answer, setAnswer] = useStateQnA('');
  const [thinking, setThinking] = useStateQnA(false);
  const scrollRef = useRefQnA(null);

  useEffectQnA(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const send = () => {
    if (!answer.trim() || thinking) return;
    const text = answer.trim();
    setAnswer('');
    setMessages((m) => [...m, { role: 'user', text }]);
    setThinking(true);
    setTimeout(() => {
      if (seq >= QUESTIONS.length) {
        setThinking(false);
        // Compose a placeholder diary from answers
        const answers = [...messages, { role: 'user', text }].filter(m => m.role === 'user').map(m => m.text);
        const diary = composeDiary(answers);
        onComplete(date, diary);
      } else {
        setSeq(seq + 1);
        setMessages((m) => [...m, { role: 'ai', text: QUESTIONS[seq], seq: seq + 1 }]);
        setThinking(false);
      }
    }, 900);
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div style={{ width: '100%', maxWidth: 640, margin: '0 auto', display: 'flex', flexDirection: 'column', height: '100vh', minHeight: 0, position: 'relative' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '18px 24px',
        borderBottom: '1px solid var(--line-faint)',
        background: 'var(--paper-bone)',
        animation: 'days-fade-in 400ms var(--ease-out) both',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onCancel}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--paper-mist)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            style={{ border: 0, background: 'transparent', padding: 6, borderRadius: 8, cursor: 'pointer', transition: 'background var(--dur-1)' }}>
            <img src="../../assets/icons/close.svg" width="18" height="18"/>
          </button>
          <div style={{ font: '500 13px/1 var(--font-mono)', color: 'var(--ink-bark)' }}>{date}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {[1,2,3,4,5].map((n) => (
            <span key={n} style={{
              width: 10, height: 10, borderRadius: 999,
              background: n < seq ? 'var(--gold-warm)' : n === seq ? 'var(--gold-soft)' : 'transparent',
              border: n === seq ? '1.5px solid var(--gold)' : n < seq ? 'none' : '1.5px dashed var(--line-strong)',
              transition: 'all var(--dur-2)',
            }}/>
          ))}
          <span style={{ font: '500 12px/1 var(--font-mono)', color: 'var(--ink-walnut)', marginLeft: 6 }}>{seq} / 5</span>
        </div>
      </div>

      {/* Scroll area */}
      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '24px 24px 140px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {messages.map((m, i) => (
          <ChatBubble key={i} role={m.role} animateDelay={i === messages.length - 1 ? 40 : 0}>{m.text}</ChatBubble>
        ))}
        {thinking && <ThinkingBubble/>}
      </div>

      {/* Sticky composer */}
      <div style={{
        position: 'absolute',
        left: 0, right: 0, bottom: 0,
        padding: '14px 24px 20px',
        background: 'rgba(251, 247, 238, 0.92)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderTop: '1px solid var(--line-faint)',
      }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <daysPrim.Textarea value={answer} onChange={setAnswer} placeholder={thinking ? '...' : '답변 입력 · Enter 전송, Shift+Enter 줄바꿈'} onKeyDown={onKey} disabled={thinking} autoFocus/>
          <daysPrim.Button disabled={!answer.trim() || thinking} onClick={send} style={{ padding: '14px 20px', borderRadius: 14 }}>
            전송
          </daysPrim.Button>
        </div>
      </div>
    </div>
  );
}

function composeDiary(answers) {
  const [moment, feeling, person, tomorrow, oneLine] = answers;
  return `오늘은 ${oneLine ? oneLine.replace(/\.$/, '') : '조용한 하루'}였다.\n\n` +
         (moment ? `가장 기억에 남는 건 ${moment} 그 순간 ${feeling || '마음이 머물렀다'}.\n\n` : '') +
         (person ? `${person} 덕분에 하루가 한결 가벼웠다. 고맙다는 말, 마음 속에라도 적어둔다.\n\n` : '') +
         (tomorrow ? `내일의 나에게 한 마디 — ${tomorrow}\n\n` : '') +
         `이 다섯 가지가 오늘의 나였다.`;
}

window.QnAChatScreen = QnAChatScreen;
