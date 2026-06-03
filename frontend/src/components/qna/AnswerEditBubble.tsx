import { useState } from 'react';

interface AnswerEditBubbleProps {
  value: string;
  onChange: (v: string) => void;
  onSave: () => void;
  onCancel: () => void;
  saving?: boolean;
}

export function AnswerEditBubble({ value, onChange, onSave, onCancel, saving }: AnswerEditBubbleProps) {
  const [focused, setFocused] = useState(false);

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'flex-end',
      animation: 'days-rise 240ms var(--ease-out) both',
    }}>
      <div style={{ maxWidth: '80%', width: '100%' }}>
        <div style={{
          padding: '12px 14px',
          borderRadius: 'var(--r-4) var(--r-4) var(--r-1) var(--r-4)',
          background: 'var(--paper-pure)',
          border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
          boxShadow: focused ? 'var(--shadow-ring)' : 'var(--shadow-1)',
          transition: 'border-color var(--dur-1), box-shadow var(--dur-1)',
        }}>
          <textarea
            value={value}
            onChange={e => onChange(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            disabled={saving}
            rows={3}
            aria-label="답변 편집"
            style={{
              width: '100%',
              resize: 'none',
              border: 0,
              outline: 0,
              background: 'transparent',
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-base)',
              lineHeight: 1.6,
              color: 'var(--ink-deep)',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <button
              type="button"
              onClick={onCancel}
              disabled={saving}
              style={{
                padding: '7px 14px',
                borderRadius: 999,
                border: '1.5px solid var(--line)',
                background: 'transparent',
                color: 'var(--ink-meta)',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                fontWeight: 500,
                cursor: saving ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.5 : 1,
                transition: 'background var(--dur-1), color var(--dur-1)',
              }}
              onMouseEnter={e => { if (!saving) (e.currentTarget as HTMLButtonElement).style.background = 'var(--sage-cloud)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
            >
              취소
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={saving || !value.trim()}
              style={{
                padding: '7px 14px',
                borderRadius: 999,
                border: 0,
                background: saving || !value.trim() ? 'var(--sage-mist)' : 'var(--sage-leaf)',
                color: 'var(--paper-pure)',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                fontWeight: 600,
                cursor: saving || !value.trim() ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.7 : 1,
                transition: 'background var(--dur-1)',
              }}
            >
              {saving ? '저장 중…' : '저장'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
