export type Mood = 'happy' | 'sad' | 'angry' | 'neutral' | 'tired';

const MOOD_EMOJI: Record<Mood, string> = {
  happy:   '😊',
  sad:     '😭',
  angry:   '😠',
  neutral: '😐',
  tired:   '😩',
};

interface MoodEmojiProps {
  mood: Mood;
  size?: number;
}

export function MoodEmoji({ mood, size = 24 }: MoodEmojiProps) {
  return (
    <span style={{ fontSize: size, lineHeight: 1, display: 'inline-block' }} aria-label={mood}>
      {MOOD_EMOJI[mood]}
    </span>
  );
}

export { MOOD_EMOJI };
