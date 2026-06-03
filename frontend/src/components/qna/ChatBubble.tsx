import { type ReactNode } from 'react';
import { Icon } from '../days/Icon';

interface ChatBubbleProps {
  role: 'ai' | 'user';
  children: ReactNode;
  onUndo?: () => void;
  undoDisabled?: boolean;
}

export function ChatBubble({ role, children, onUndo, undoDisabled }: ChatBubbleProps) {
  const isUser = role === 'user';
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      animation: 'days-rise 240ms var(--ease-out) both',
    }}>
      <div style={{ position: 'relative', maxWidth: '80%' }}>
        {isUser && onUndo && (
          <button
            type="button"
            aria-label="답변 수정"
            onClick={undoDisabled ? undefined : onUndo}
            disabled={undoDisabled}
            style={{
              position: 'absolute',
              top: -10,
              right: -10,
              width: 24,
              height: 24,
              borderRadius: '50%',
              border: '1px solid var(--line)',
              background: 'var(--paper-pure)',
              boxShadow: 'var(--shadow-1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: undoDisabled ? 'not-allowed' : 'pointer',
              opacity: undoDisabled ? 0.4 : 1,
              zIndex: 1,
              color: 'var(--ink-meta)',
              padding: 0,
              transition: 'background var(--dur-1), color var(--dur-1)',
            }}
            onMouseEnter={e => {
              if (!undoDisabled) {
                (e.currentTarget as HTMLButtonElement).style.background = 'var(--sage-wash)';
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--sage-leaf)';
              }
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'var(--paper-pure)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-meta)';
            }}
          >
            <Icon name="pencil" size={13} />
          </button>
        )}
        <div style={{
          padding: '12px 16px',
          borderRadius: isUser ? 'var(--r-4) var(--r-4) var(--r-1) var(--r-4)' : 'var(--r-4) var(--r-4) var(--r-4) var(--r-1)',
          background: isUser ? 'var(--bubble-user)' : 'var(--bubble-ai)',
          color: isUser ? 'var(--bubble-text-user)' : 'var(--bubble-text-ai)',
          border: isUser ? 'none' : '1px solid var(--bubble-border-ai)',
          boxShadow: 'var(--shadow-1)',
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--t-base)',
          lineHeight: 1.6,
        }}>
          {children}
        </div>
      </div>
    </div>
  );
}
