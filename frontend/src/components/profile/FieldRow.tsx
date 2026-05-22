import { type ReactNode } from 'react';

interface FieldRowProps {
  label: string;
  value: ReactNode;
}

export function FieldRow({ label, value }: FieldRowProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: 12,
      padding: '8px 0',
      borderBottom: '1px solid var(--line-faint)',
    }}>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-sm)', color: 'var(--ink-meta)', minWidth: 72, flexShrink: 0 }}>
        {label}
      </span>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-base)', color: 'var(--ink-body)', textAlign: 'right' }}>
        {value || <span style={{ color: 'var(--ink-hint)' }}>미입력</span>}
      </span>
    </div>
  );
}
