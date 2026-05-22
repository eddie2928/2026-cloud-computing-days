import { type ReactNode, useState } from 'react';

interface SectionCardProps {
  title: string;
  children: ReactNode;
  editContent?: ReactNode;
}

export function SectionCard({ title, children, editContent }: SectionCardProps) {
  const [editing, setEditing] = useState(false);

  return (
    <div style={{
      background: 'var(--paper-pure)',
      borderRadius: 'var(--r-5)',
      border: '1px solid var(--line-faint)',
      boxShadow: 'var(--shadow-card)',
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 18px',
        borderBottom: editing ? '1px solid var(--line-faint)' : 'none',
      }}>
        <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 'var(--t-sm)', color: 'var(--ink-meta)', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
          {title}
        </span>
        {editContent && (
          <button
            onClick={() => setEditing(e => !e)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-sm)',
              fontWeight: 500,
              color: editing ? 'var(--accent-clay)' : 'var(--sage-leaf)',
              padding: '2px 8px',
            }}
          >
            {editing ? '닫기' : '수정'}
          </button>
        )}
      </div>
      <div style={{ padding: '12px 18px' }}>
        {editing && editContent ? editContent : children}
      </div>
    </div>
  );
}
