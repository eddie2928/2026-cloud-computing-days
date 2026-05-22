import { useState, type KeyboardEvent } from 'react'
import { Icon } from './Icon'

interface TagInputProps {
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  ariaLabel?: string
}

export function TagInput({ value, onChange, placeholder, ariaLabel }: TagInputProps) {
  const [draft, setDraft] = useState('')
  const [focused, setFocused] = useState(false)

  const commitDraft = () => {
    const tag = draft.trim()
    if (!tag) return
    if (value.includes(tag)) {
      setDraft('')
      return
    }
    onChange([...value, tag])
    setDraft('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return
    if (e.key === 'Enter') {
      e.preventDefault()
      commitDraft()
    }
  }

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag))
  }

  const canSave = draft.trim().length > 0 && !value.includes(draft.trim())

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 4px 4px 10px',
          minHeight: 44,
          border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
          background: 'var(--paper-pure)',
          borderRadius: 12,
          boxShadow: focused ? 'var(--shadow-ring)' : 'none',
          transition: 'border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out)',
        }}
      >
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          aria-label={ariaLabel ?? '태그 입력'}
          style={{
            flex: 1,
            minWidth: 0,
            border: 'none',
            outline: 'none',
            padding: '4px 6px',
            font: '400 14px/1.4 var(--font-sans)',
            color: 'var(--ink-deep)',
            background: 'transparent',
          }}
        />
        <button
          type="button"
          onClick={commitDraft}
          disabled={!canSave}
          aria-label="태그 저장"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 36,
            height: 36,
            borderRadius: 10,
            border: 'none',
            background: canSave ? 'var(--sage-leaf)' : 'var(--sage-mist)',
            color: 'var(--paper-pure)',
            cursor: canSave ? 'pointer' : 'not-allowed',
            transition: 'background 160ms var(--ease-out)',
          }}
        >
          <Icon name="save" size={18} color="var(--paper-pure)" />
        </button>
      </div>

      {value.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {value.map((tag) => (
            <span
              key={tag}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '4px 8px 4px 10px',
                borderRadius: 999,
                background: 'var(--sage-leaf)',
                color: 'var(--paper-pure)',
                font: '500 13px/1 var(--font-sans)',
              }}
            >
              {tag}
              <button
                type="button"
                aria-label={`${tag} 삭제`}
                onClick={() => removeTag(tag)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--paper-pure)',
                  cursor: 'pointer',
                  padding: 2,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  lineHeight: 1,
                  fontSize: 14,
                }}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
