import { type EmotionKey } from '../../lib/emotions'

export type Mood = EmotionKey

/* Days — Cloud Mood Emoticons
 * 5가지 감정을 각자의 시그니처 색을 입힌 구름 얼굴로 표현합니다.
 *   happy 행복(노랑) · sad 슬픔(파랑) · angry 화남(빨강) · neutral 평이(초록) · bored 따분(베이지)
 * 기존 MoodEmoji와 props(mood, size) / export가 동일하므로 이 파일만 교체하면 됩니다.
 */

type Palette = { body: string; deep: string; ink: string; cheek: string }

const PALETTE: Record<EmotionKey, Palette> = {
  happy:   { body: '#FFDE8A', deep: '#F4C24B', ink: '#6B5212', cheek: '#F39B86' },
  angry:   { body: '#F4A28E', deep: '#E15B3C', ink: '#7C2B1A', cheek: '#D9583F' },
  sad:     { body: '#AECDF0', deep: '#5B8FD6', ink: '#274C77', cheek: '#88B4E6' },
  bored:   { body: '#D8D2BC', deep: '#A89F80', ink: '#5A5440', cheek: '#C9A99A' },
  neutral: { body: '#C6E0B0', deep: '#7D9D6A', ink: '#3D4A30', cheek: '#EBB0A6' },
}

function cheeks(c: Palette) {
  return (
    <>
      <ellipse cx="72" cy="104" rx="11" ry="7" fill={c.cheek} opacity="0.55" />
      <ellipse cx="150" cy="104" rx="11" ry="7" fill={c.cheek} opacity="0.55" />
    </>
  )
}

function Face({ mood, c }: { mood: EmotionKey; c: Palette }) {
  const k = c.ink
  switch (mood) {
    case 'happy':
      return (
        <>
          <path d="M82 90 Q90 80 98 90" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M124 90 Q132 80 140 90" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          {cheeks(c)}
          <path d="M96 104 Q111 124 126 104 Z" fill={k} />
          <path d="M101 113 Q111 121 121 113 Z" fill={c.cheek} />
        </>
      )
    case 'angry':
      return (
        <>
          <path d="M80 78 L100 86" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M140 78 L120 86" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <circle cx="93" cy="93" r="4.5" fill={k} />
          <circle cx="127" cy="93" r="4.5" fill={k} />
          {cheeks(c)}
          <path d="M100 112 Q111 104 122 112" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
        </>
      )
    case 'sad':
      return (
        <>
          <path d="M84 92 Q91 86 98 92" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M124 92 Q131 86 138 92" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          {cheeks(c)}
          <path d="M98 118 Q111 108 124 118" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M140 96 q-8 12 0 17 q8 -5 0 -17 Z" fill={c.deep} />
          <ellipse cx="138.5" cy="108" rx="2.2" ry="3" fill="#ffffff" opacity="0.55" />
        </>
      )
    case 'bored':
      return (
        <>
          <path d="M82 90 h18" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M122 90 h18" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
          <path d="M82 84 q9 -5 18 0" stroke={k} strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.5" />
          <path d="M122 84 q9 -5 18 0" stroke={k} strokeWidth="3" fill="none" strokeLinecap="round" opacity="0.5" />
          {cheeks(c)}
          <path d="M101 110 h20" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
        </>
      )
    case 'neutral':
    default:
      return (
        <>
          <circle cx="93" cy="90" r="5" fill={k} />
          <circle cx="127" cy="90" r="5" fill={k} />
          {cheeks(c)}
          <path d="M100 108 Q111 116 122 108" stroke={k} strokeWidth="5" fill="none" strokeLinecap="round" />
        </>
      )
  }
}

interface MoodEmojiProps {
  mood: Mood
  size?: number
  /** 위아래로 살짝 떠다니는 애니메이션 (기본 false) */
  float?: boolean
}

export function MoodEmoji({ mood, size = 24, float = false }: MoodEmojiProps) {
  const c = PALETTE[mood] ?? PALETTE.neutral
  const id = `clip-${mood}`
  return (
    <svg
      width={size}
      height={(size * 168) / 220}
      viewBox="0 0 220 168"
      fill="none"
      role="img"
      aria-label={mood}
      style={float ? { animation: 'mood-float 3.4s ease-in-out infinite', willChange: 'transform' } : undefined}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <clipPath id={id}>
          <rect x="34" y="74" width="152" height="60" rx="30" />
          <circle cx="64" cy="84" r="32" />
          <circle cx="100" cy="58" r="42" />
          <circle cx="144" cy="62" r="38" />
          <circle cx="174" cy="88" r="30" />
        </clipPath>
      </defs>

      {/* 그림자 */}
      <ellipse cx="110" cy="150" rx="74" ry="13" fill="rgba(54,70,38,0.10)" />

      {/* 구름 본체 */}
      <g clipPath={`url(#${id})`}>
        <rect x="34" y="74" width="152" height="60" rx="30" fill={c.body} />
        <circle cx="64" cy="84" r="32" fill={c.body} />
        <circle cx="100" cy="58" r="42" fill={c.body} />
        <circle cx="144" cy="62" r="38" fill={c.body} />
        <circle cx="174" cy="88" r="30" fill={c.body} />
        <ellipse cx="110" cy="150" rx="92" ry="34" fill={c.deep} opacity="0.18" />
        <ellipse cx="92" cy="46" rx="30" ry="16" fill="#ffffff" opacity="0.45" />
      </g>

      {/* 얼굴 */}
      <Face mood={mood} c={c} />
    </svg>
  )
}

/* 일부 화면(예: PetCard, 호환용)에서 import 하던 이름 유지.
 * 더 이상 이모지 문자열은 쓰지 않지만, 깨지지 않도록 라벨로 매핑해 둡니다. */
export const MOOD_EMOJI: Record<EmotionKey, string> = {
  happy: '행복',
  sad: '슬픔',
  angry: '화남',
  neutral: '평이',
  bored: '따분',
}
