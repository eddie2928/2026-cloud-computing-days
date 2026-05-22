import { type ReactNode } from 'react';

type ChipVariant = 'pill' | 'segment';

interface ChipProps {
  children?: ReactNode;
  active?: boolean;
  onClick?: () => void;
  variant?: ChipVariant;
  icon?: ReactNode;
}

export function Chip({ children, active, onClick, variant = 'pill', icon }: ChipProps) {
  if (variant === 'segment') {
    return (
      <button
        onClick={onClick}
        style={{
          flex: 1,
          padding: '14px 8px',
          borderRadius: 'var(--r-pill)',
          border: active ? '0' : '1.5px solid var(--line)',
          background: active ? 'var(--sage-leaf)' : 'var(--paper-pure)',
          color: active ? 'var(--paper-pure)' : 'var(--ink-body)',
          fontFamily: 'var(--font-sans)',
          fontWeight: 500,
          fontSize: 'var(--t-base)',
          cursor: 'pointer',
          boxShadow: active ? 'var(--shadow-card)' : 'none',
          transition: 'background var(--dur-1), color var(--dur-1)',
        }}
      >{children}</button>
    );
  }
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '8px 14px',
        borderRadius: 'var(--r-pill)',
        border: active ? '0' : '1.5px solid var(--line)',
        background: active ? 'var(--sage-leaf)' : 'var(--paper-pure)',
        color: active ? 'var(--paper-pure)' : 'var(--ink-body)',
        fontFamily: 'var(--font-sans)',
        fontWeight: 500,
        fontSize: 'var(--t-sm)',
        cursor: 'pointer',
        transition: 'background var(--dur-1), color var(--dur-1)',
      }}
    >{icon}{children}</button>
  );
}
