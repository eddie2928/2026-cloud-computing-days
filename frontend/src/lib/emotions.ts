export const EMOTION_KEYS = ['happy', 'sad', 'angry', 'neutral', 'bored'] as const
export type EmotionKey = typeof EMOTION_KEYS[number]

export const EMOTION_EMOJI: Record<EmotionKey, string> = {
  happy: '😊',
  sad: '😭',
  angry: '😠',
  neutral: '😐',
  bored: '😩',
}

export const EMOTION_LABEL: Record<EmotionKey, string> = {
  happy: '행복',
  sad: '슬픔',
  angry: '화남',
  neutral: '보통',
  bored: '지루함',
}
