import { Icon } from '../days/Icon'

interface SearchTriggerCardProps {
  onClick: () => void
}

export function SearchTriggerCard({ onClick }: SearchTriggerCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        flex: 1,
        textAlign: 'left',
        background: 'var(--paper-pure)',
        borderRadius: 'var(--r-5)',
        border: '1px solid var(--line-faint)',
        boxShadow: 'var(--shadow-card)',
        padding: '20px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        cursor: 'pointer',
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          fontFamily: 'var(--font-sans)',
          fontWeight: 600,
          fontSize: 'var(--t-sm)',
          color: 'var(--ink-meta)',
          letterSpacing: '0.02em',
          textTransform: 'uppercase',
        }}
      >
        <Icon name="book" size={16} color="var(--sage-forest)" />
        검색
      </div>
      <div
        style={{
          margin: 0,
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--t-base)',
          color: 'var(--ink-body)',
        }}
      >
        키워드로 찾아보기
      </div>
      <span
        style={{
          alignSelf: 'flex-start',
          padding: '6px 14px',
          borderRadius: 999,
          background: 'var(--sage-leaf)',
          color: 'var(--paper-pure)',
          font: '600 13px/1 var(--font-sans)',
        }}
      >
        열기
      </span>
    </button>
  )
}
