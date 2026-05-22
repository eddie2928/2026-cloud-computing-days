import { useEffect, useMemo, useState } from 'react'
import { type CalendarEntry } from '../../lib/week'
import { searchEntries } from '../../lib/search'
import { PillInput } from '../days/PillInput'
import { Icon } from '../days/Icon'

interface SearchModalProps {
  entries: CalendarEntry[]
  onClose: () => void
  onSelect: (date: string) => void
}

export function SearchModal({ entries, onClose, onSelect }: SearchModalProps) {
  const [q, setQ] = useState('')

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const results = useMemo(() => searchEntries(entries, q), [entries, q])

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="일기 검색"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '15vh',
        zIndex: 1000,
        animation: 'days-fade-in 200ms var(--ease-out) both',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--paper-pure)',
          borderRadius: 20,
          width: '92%',
          maxWidth: 420,
          maxHeight: '70vh',
          overflowY: 'auto',
          padding: 20,
          boxShadow: 'var(--shadow-3)',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontWeight: 700,
              fontSize: 'var(--t-md)',
              color: 'var(--sage-ink)',
            }}
          >
            검색
          </span>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 20,
              cursor: 'pointer',
              color: 'var(--ink-meta)',
              lineHeight: 1,
              padding: '4px 8px',
            }}
          >
            ×
          </button>
        </div>

        <PillInput
          value={q}
          onChange={setQ}
          placeholder="날짜로 검색 (예: 05-15)"
          ariaLabel="일기 검색 입력"
          icon={<Icon name="book" size={16} />}
        />

        {q && results.length === 0 && (
          <p
            style={{
              margin: 0,
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-sm)',
              color: 'var(--ink-hint)',
              textAlign: 'center',
              padding: '8px 0',
            }}
          >
            결과가 없어요
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map((entry) => (
            <button
              key={entry.date}
              type="button"
              onClick={() => onSelect(entry.date)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'var(--paper-bone)',
                border: '1px solid var(--line-faint)',
                borderRadius: 'var(--r-3)',
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                fontSize: 'var(--t-base)',
                color: 'var(--ink-body)',
              }}
            >
              <span>{entry.date}</span>
              <Icon name="chevron-right" size={16} color="var(--ink-hint)" />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
