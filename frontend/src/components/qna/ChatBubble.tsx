import { type ReactNode } from 'react';

interface ChatBubbleProps {
  role: 'ai' | 'user';
  children: ReactNode;
}

export function ChatBubble({ role, children }: ChatBubbleProps) {
  const isUser = role === 'user';
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      animation: 'days-rise 240ms var(--ease-out) both',
    }}>
      <div style={{
        maxWidth: '80%',
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
  );
}
