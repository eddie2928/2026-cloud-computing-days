import { useState } from 'react'

const MAX_CHARS = 5000

interface DiaryBodyCardProps {
  body: string
  date?: string
  onSave?: (newBody: string) => Promise<void>
}

export function DiaryBodyCard({ body, date, onSave }: DiaryBodyCardProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(body)
  const [saving, setSaving] = useState(false)

  const handleEdit = () => {
    setDraft(body)
    setEditing(true)
  }

  const handleCancel = () => {
    setEditing(false)
    setDraft(body)
  }

  const handleSave = async () => {
    if (!onSave) return
    setSaving(true)
    try {
      await onSave(draft)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <div style={{
        background: 'var(--paper-warm)',
        borderRadius: 'var(--r-5)',
        border: '1px solid var(--sage-mist)',
        boxShadow: 'var(--shadow-2)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}>
        <textarea
          aria-label="일기 본문 편집"
          value={draft}
          onChange={e => setDraft(e.target.value.slice(0, MAX_CHARS))}
          maxLength={MAX_CHARS}
          style={{
            width: '100%',
            minHeight: 200,
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--t-md)',
            color: 'var(--sage-ink)',
            lineHeight: 1.85,
            border: 'none',
            background: 'transparent',
            resize: 'vertical',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--ink-hint)' }}>
            {draft.length} / {MAX_CHARS}
          </span>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              onClick={handleCancel}
              style={{
                background: 'none', border: '1px solid var(--line-faint)',
                borderRadius: 20, padding: '6px 16px',
                fontFamily: 'var(--font-sans)', cursor: 'pointer', fontSize: 14,
                color: 'var(--ink-meta)',
              }}
            >
              취소
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || draft.length === 0}
              style={{
                background: 'var(--sage-leaf)', border: 'none',
                borderRadius: 20, padding: '6px 16px',
                fontFamily: 'var(--font-sans)', cursor: 'pointer', fontSize: 14,
                color: '#fff',
              }}
            >
              {saving ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      background: 'var(--paper-warm)',
      borderRadius: 'var(--r-5)',
      border: '1px solid var(--line-faint)',
      boxShadow: 'var(--shadow-2)',
      padding: '24px 20px',
      position: 'relative',
    }}>
      <p style={{
        margin: 0,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--t-md)',
        color: 'var(--sage-ink)',
        lineHeight: 1.85,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {body}
      </p>
      {onSave && (
        <button
          type="button"
          aria-label="편집"
          onClick={handleEdit}
          style={{
            position: 'absolute', top: 12, right: 12,
            background: 'none', border: 'none',
            cursor: 'pointer', fontSize: 16, color: 'var(--ink-hint)',
            padding: 4,
          }}
        >
          ✏️
        </button>
      )}
    </div>
  )
}
