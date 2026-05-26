interface ScheduleCardProps {
  schedule: { period_start: string; period_end: string; situation: string }
  onAccept: () => void
  onReject: () => void
  status: 'pending' | 'accepted' | 'rejected'
}

export function ScheduleCard({ schedule, onAccept, onReject, status }: ScheduleCardProps) {
  return (
    <div
      style={{
        background: 'var(--paper-pure)',
        border: '1px solid var(--line)',
        borderRadius: 'var(--r-4, 18px)',
        padding: 16,
        margin: '6px 0',
        opacity: status === 'accepted' ? 0.7 : status === 'rejected' ? 0.45 : 1,
        animation: 'days-slide-in 380ms var(--ease-out) both',
        transition: 'opacity 200ms',
      }}
    >
      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, lineHeight: 1, color: 'var(--ink-meta)', margin: '0 0 8px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        일정 추가
      </p>
      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 400, fontSize: 15, lineHeight: 1.4, color: 'var(--ink-deep)', margin: '0 0 4px' }}>
        {schedule.situation}
      </p>
      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 400, fontSize: 12, lineHeight: 1, color: 'var(--ink-hint)', margin: '0 0 12px' }}>
        {schedule.period_start} ~ {schedule.period_end}
      </p>

      {status === 'pending' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={onAccept}
            style={{
              background: 'var(--sage-leaf)',
              border: 'none',
              borderRadius: 'var(--r-pill, 999px)',
              padding: '6px 16px',
              fontFamily: 'var(--font-sans)',
              fontWeight: 600,
              fontSize: 13,
              color: 'var(--paper-pure)',
              cursor: 'pointer',
            }}
          >
            추가
          </button>
          <button
            onClick={onReject}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '6px 12px',
              fontFamily: 'var(--font-sans)',
              fontWeight: 500,
              fontSize: 13,
              color: 'var(--ink-meta)',
              cursor: 'pointer',
            }}
          >
            무시
          </button>
        </div>
      )}

      {status === 'accepted' && (
        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--sage-leaf)', margin: 0, display: 'flex', alignItems: 'center', gap: 4 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          추가됨
        </p>
      )}

      {status === 'rejected' && (
        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-meta)', margin: 0 }}>
          무시됨
        </p>
      )}
    </div>
  )
}
