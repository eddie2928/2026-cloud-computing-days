import { useState } from 'react'
import client from '../../api/client'
import { type ScheduleItem } from '../../lib/week'

interface SchedulePopupProps {
  schedule: ScheduleItem
  onClose: () => void
  onUpdated: () => void
}

export function SchedulePopup({ schedule, onClose, onUpdated }: SchedulePopupProps) {
  const [mode, setMode] = useState<'view' | 'edit' | 'delete-confirm'>('edit')
  const [situation, setSituation] = useState(schedule.situation)
  const [periodStart, setPeriodStart] = useState(schedule.period_start)
  const [periodEnd, setPeriodEnd] = useState(schedule.period_end)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await client.patch(`/schedules/${schedule.id}`, {
        situation,
        period_start: periodStart,
        period_end: periodEnd,
      })
      onUpdated()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setSaving(true)
    try {
      await client.delete(`/schedules/${schedule.id}`)
      onUpdated()
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(46, 36, 24, 0.32)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--paper-cream)',
          border: '1px solid var(--line)',
          borderRadius: 'var(--r-5, 24px)',
          boxShadow: 'var(--shadow-3)',
          padding: 24,
          width: '100%',
          maxWidth: 360,
          position: 'relative',
          animation: 'days-rise 280ms var(--ease-out) both',
        }}
      >
        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          aria-label="닫기"
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 4,
            color: 'var(--ink-stone)',
            lineHeight: 0,
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        {mode === 'view' && (
          <>
            <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, lineHeight: 1, color: 'var(--gold-deep)', margin: '0 0 10px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              일정
            </p>
            <p style={{ fontFamily: 'var(--font-serif)', fontWeight: 400, fontSize: 18, lineHeight: 1.3, color: 'var(--ink-coffee)', margin: '0 0 8px' }}>
              {schedule.situation}
            </p>
            <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 400, fontSize: 13, lineHeight: 1, color: 'var(--ink-bark)', margin: '0 0 20px' }}>
              {schedule.period_start} ~ {schedule.period_end}
            </p>
            <hr style={{ border: 'none', borderTop: '1px solid var(--line-faint)', margin: '0 0 16px' }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setMode('edit')}
                style={{
                  flex: 1,
                  background: 'var(--paper-cream)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-3, 12px)',
                  padding: '8px 0',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 500,
                  fontSize: 14,
                  color: 'var(--ink-coffee)',
                  cursor: 'pointer',
                }}
              >
                수정
              </button>
              <button
                onClick={() => setMode('delete-confirm')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 'var(--r-3, 12px)',
                  padding: '8px 16px',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 500,
                  fontSize: 14,
                  color: 'var(--clay)',
                  cursor: 'pointer',
                }}
              >
                삭제
              </button>
            </div>
          </>
        )}

        {mode === 'edit' && (
          <>
            <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, lineHeight: 1, color: 'var(--gold-deep)', margin: '0 0 16px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              일정 수정
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 20 }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-stone)' }}>내용</span>
                <input
                  value={situation}
                  onChange={e => setSituation(e.target.value)}
                  style={{
                    background: 'var(--paper-mist)',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    padding: '8px 12px',
                    fontFamily: 'var(--font-sans)',
                    fontSize: 14,
                    color: 'var(--ink-coffee)',
                    outline: 'none',
                    width: '100%',
                    boxSizing: 'border-box',
                  }}
                  onFocus={e => { e.currentTarget.style.boxShadow = 'var(--shadow-glow)'; }}
                  onBlur={e => { e.currentTarget.style.boxShadow = 'none'; }}
                />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-stone)' }}>시작일</span>
                <input
                  type="date"
                  value={periodStart}
                  onChange={e => setPeriodStart(e.target.value)}
                  style={{
                    background: 'var(--paper-mist)',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    padding: '8px 12px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 14,
                    color: 'var(--ink-coffee)',
                    outline: 'none',
                    width: '100%',
                    boxSizing: 'border-box',
                  }}
                />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-stone)' }}>종료일</span>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={e => setPeriodEnd(e.target.value)}
                  style={{
                    background: 'var(--paper-mist)',
                    border: '1px solid var(--line)',
                    borderRadius: 12,
                    padding: '8px 12px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 14,
                    color: 'var(--ink-coffee)',
                    outline: 'none',
                    width: '100%',
                    boxSizing: 'border-box',
                  }}
                />
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  flex: 1,
                  background: 'linear-gradient(135deg, var(--gold-deep), var(--gold))',
                  border: 'none',
                  borderRadius: 'var(--r-pill, 999px)',
                  padding: '10px 0',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 600,
                  fontSize: 14,
                  color: 'var(--ink-coffee)',
                  cursor: saving ? 'default' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                저장
              </button>
              <button
                onClick={() => setMode('view')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 'var(--r-3, 12px)',
                  padding: '10px 16px',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 500,
                  fontSize: 14,
                  color: 'var(--ink-stone)',
                  cursor: 'pointer',
                }}
              >
                취소
              </button>
            </div>
          </>
        )}

        {mode === 'delete-confirm' && (
          <>
            <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, lineHeight: 1, color: 'var(--clay)', margin: '0 0 12px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              삭제 확인
            </p>
            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--ink-coffee)', margin: '0 0 20px' }}>
              이 일정을 삭제합니다.
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleDelete}
                disabled={saving}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: '1px solid var(--clay)',
                  borderRadius: 'var(--r-3, 12px)',
                  padding: '9px 0',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 600,
                  fontSize: 14,
                  color: 'var(--clay)',
                  cursor: saving ? 'default' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                확인
              </button>
              <button
                onClick={() => setMode('view')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 'var(--r-3, 12px)',
                  padding: '9px 16px',
                  fontFamily: 'var(--font-sans)',
                  fontWeight: 500,
                  fontSize: 14,
                  color: 'var(--ink-stone)',
                  cursor: 'pointer',
                }}
              >
                취소
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
