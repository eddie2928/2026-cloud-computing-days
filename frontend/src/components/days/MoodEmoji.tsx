import { EMOTION_EMOJI, type EmotionKey } from '../../lib/emotions'

export type Mood = EmotionKey

interface MoodEmojiProps {
  mood: Mood
  size?: number
}

export function MoodEmoji({ mood, size = 24 }: MoodEmojiProps) {
  return (
    <span style={{ fontSize: size, lineHeight: 1, display: 'inline-block' }} aria-label={mood}>
      {EMOTION_EMOJI[mood]}
    </span>
  )
}

export { EMOTION_EMOJI as MOOD_EMOJI }
