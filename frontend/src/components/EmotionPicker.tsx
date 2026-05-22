import { EMOTION_KEYS, EMOTION_EMOJI, EMOTION_LABEL, type EmotionKey } from '../lib/emotions'

interface EmotionPickerProps {
  value: EmotionKey
  onChange: (v: EmotionKey) => void
}

export function EmotionPicker({ value, onChange }: EmotionPickerProps) {
  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
      {EMOTION_KEYS.map((key) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          title={EMOTION_LABEL[key]}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 4,
            padding: '8px 12px',
            borderRadius: 8,
            border: value === key ? '2px solid #4f46e5' : '2px solid #e5e7eb',
            background: value === key ? '#eef2ff' : 'white',
            cursor: 'pointer',
            fontSize: 12,
            color: '#374151',
          }}
        >
          <span style={{ fontSize: 28 }}>{EMOTION_EMOJI[key]}</span>
          {EMOTION_LABEL[key]}
        </button>
      ))}
    </div>
  )
}
