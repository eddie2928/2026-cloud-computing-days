import { MoodPickerInline } from '../diary/MoodPickerInline'
import { DiaryBodyCard } from '../diary/DiaryBodyCard'
import { type Mood } from '../days/MoodEmoji'

interface DiaryModalContentProps {
  date: string
  body: string
  emotion?: string
}

export function DiaryModalContent({ date, body, emotion }: DiaryModalContentProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontWeight: 700,
          fontSize: 'var(--t-md)',
          color: 'var(--sage-ink)',
          letterSpacing: '-0.01em',
        }}
      >
        {date}
      </div>
      <MoodPickerInline date={date} initial={emotion as Mood | undefined} />
      <DiaryBodyCard body={body} />
    </div>
  )
}
