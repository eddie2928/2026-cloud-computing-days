import { type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../days/Icon';

interface HeaderProps {
  title?: string;
  showBack?: boolean;
  action?: ReactNode;
}

export function Header({ title, showBack = false, action }: HeaderProps) {
  const navigate = useNavigate();

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 16px',
      minHeight: 52,
    }}>
      <div style={{ width: 40 }}>
        {showBack && (
          <button
            aria-label="뒤로 가기"
            onClick={() => navigate(-1)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--ink-body)',
              padding: 4,
            }}
          >
            <Icon name="arrow-left" size={22} />
          </button>
        )}
      </div>
      {title && (
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontWeight: 600,
          fontSize: 'var(--t-md)',
          color: 'var(--sage-ink)',
          flex: 1,
          textAlign: 'center',
        }}>{title}</span>
      )}
      <div style={{ width: 40, display: 'flex', justifyContent: 'flex-end' }}>
        {action}
      </div>
    </header>
  );
}
