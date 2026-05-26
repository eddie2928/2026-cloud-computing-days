/* global window */
const { useState, useRef, useEffect, CloudLeaf, Icon } = window.DaysUI;

const QUESTIONS = [
  '오늘 하루는 어떠셨나요?',
  '기억에 남는 순간이 있었나요?',
  '오늘 가장 고마웠던 일은 무엇인가요?',
  '아쉬웠거나 마음에 걸린 일이 있었나요?',
  '내일을 위해 어떤 한 가지를 남겨두고 싶나요?',
];

function ThinkingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', padding: '2px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%',
          background: 'var(--sage-leaf)',
          animation: `days-thinking 1.2s ease-in-out ${i * 0.18}s infinite`,
        }} />
      ))}
    </span>
  );
}

function CloudAvatar() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: '50%',
      background: 'var(--sage-cloud)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <Icon name="cloud" size={18} color="var(--sage-forest)" />
    </div>
  );
}

function Bubble({ role, children, animationDelay = 0 }) {
  const isUser = role === 'user';
  return (
    <div style={{
      display: 'flex',
      gap: 8,
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start',
      animation: `days-rise 380ms var(--ease-out) ${animationDelay}ms both`,
    }}>
      {!isUser && <CloudAvatar />}
      <div style={{
        maxWidth: '78%',
        padding: '10px 16px',
        borderRadius: isUser ? '20px 6px 20px 20px' : '6px 20px 20px 20px',
        background: isUser ? 'var(--bubble-user)' : 'var(--bubble-ai)',
        color: isUser ? 'var(--bubble-text-user)' : 'var(--bubble-text-ai)',
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--t-base)',
        lineHeight: 1.5,
        boxShadow: isUser ? 'none' : 'var(--shadow-1)',
      }}>
        {children}
      </div>
    </div>
  );
}

function ChatScreen({ date = '5월 22일 (목)', onClose, onComplete }) {
  const [step, setStep] = useState(2);          // we've already answered 1
  const [thinking, setThinking] = useState(false);
  const [answer, setAnswer] = useState('');
  const [messages, setMessages] = useState([
    { role: 'ai',   text: QUESTIONS[0] },
    { role: 'user', text: '평온했어요 😊' },
    { role: 'ai',   text: QUESTIONS[1] },
    { role: 'user', text: '산책하다 노을을 봤어요' },
  ]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const send = () => {
    if (!answer.trim() || thinking) return;
    const newMessages = [...messages, { role: 'user', text: answer.trim() }];
    setMessages(newMessages);
    setAnswer('');
    setThinking(true);
    setTimeout(() => {
      const nextStep = step + 1;
      if (nextStep > 5) {
        setThinking(false);
        onComplete && onComplete();
        return;
      }
      setMessages(m => [...m, { role: 'ai', text: QUESTIONS[nextStep - 1] }]);
      setStep(nextStep);
      setThinking(false);
    }, 900);
  };

  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: 'rgba(46, 59, 31, 0.30)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px 12px 12px',
      animation: 'days-fade-in 240ms var(--ease-out) both',
      zIndex: 10,
    }}>
      <div style={{
        width: '100%',
        height: '100%',
        background: 'linear-gradient(180deg, var(--paper-warm) 0%, var(--sage-paper) 100%)',
        borderRadius: 'var(--r-6)',
        boxShadow: 'var(--shadow-3)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'days-pop 380ms var(--ease-soft) both',
      }}>
        {/* Header */}
        <header style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '18px 20px 14px',
          gap: 10,
          borderBottom: '1px solid var(--line-faint)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'var(--sage-cloud)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon name="cloud" size={20} color="var(--sage-forest)" />
            </div>
            <div>
              <div className="t-h3" style={{ fontWeight: 600 }}>오늘의 기록 가이드</div>
              <div className="t-meta" style={{ fontSize: 'var(--t-xs)' }}>{date}</div>
            </div>
          </div>
          <button onClick={onClose} aria-label="닫기" style={{
            background: 'transparent', border: 0, cursor: 'pointer', padding: 4,
          }}>
            <Icon name="close" size={22} color="var(--ink-meta)" />
          </button>
        </header>

        {/* Messages */}
        <div ref={scrollRef} style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 18px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}>
          {messages.map((m, i) => (
            <Bubble key={i} role={m.role} animationDelay={i * 40}>{m.text}</Bubble>
          ))}
          {thinking && (
            <Bubble role="ai" animationDelay={0}>
              <ThinkingDots />
            </Bubble>
          )}
        </div>

        {/* Progress + composer */}
        <div style={{
          padding: '0 20px 8px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          <div style={{ flex: 1, height: 4, background: 'var(--sage-cloud)', borderRadius: 'var(--r-pill)', overflow: 'hidden' }}>
            <div style={{
              width: `${(step / 5) * 100}%`,
              height: '100%',
              background: 'var(--sage-leaf)',
              transition: 'width var(--dur-3) var(--ease-out)',
            }} />
          </div>
          <span className="t-mono" style={{ fontSize: 'var(--t-xs)', color: 'var(--ink-meta)' }}>{step} / 5</span>
        </div>

        <div style={{
          padding: '8px 16px 16px',
          display: 'flex',
          gap: 8,
          alignItems: 'center',
        }}>
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); send(); } }}
            placeholder="답변을 입력하세요"
            style={{
              flex: 1,
              padding: '12px 18px',
              borderRadius: 'var(--r-pill)',
              border: '1px solid var(--line)',
              background: 'var(--paper-pure)',
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-base)',
              color: 'var(--ink-deep)',
              outline: 0,
              boxShadow: 'var(--shadow-1)',
            }}
          />
          <button onClick={send} aria-label="전송" disabled={!answer.trim() || thinking} style={{
            width: 44, height: 44,
            borderRadius: '50%',
            background: !answer.trim() || thinking ? 'var(--sage-mist)' : 'var(--sage-forest)',
            border: 0,
            cursor: !answer.trim() || thinking ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'var(--shadow-card)',
            transition: 'background var(--dur-1)',
          }}>
            <Icon name="arrow-up" size={22} color="var(--paper-pure)" />
          </button>
        </div>
      </div>
    </div>
  );
}

window.ChatScreen = ChatScreen;
