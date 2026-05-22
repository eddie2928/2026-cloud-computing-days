import type { CSSProperties } from 'react'

interface DaisyProps {
  size?: number
  petalFill?: string
  petalStroke?: string
  centerFill?: string
  centerStroke?: string
  spin?: boolean
  style?: CSSProperties
}

export function Daisy({
  size = 14,
  petalFill = '#FFFFFF',
  petalStroke = '#D5A646',
  centerFill = '#D5A646',
  centerStroke = '#A7842D',
  spin = false,
  style,
}: DaisyProps) {
  const petal =
    'M 12 11 C 9.5 11, 7.6 8.5, 7.6 5.6 C 7.6 2.4, 9.5 0.4, 12 0.4 C 14.5 0.4, 16.4 2.4, 16.4 5.6 C 16.4 8.5, 14.5 11, 12 11 Z'
  return (
    <svg
      width={size}
      height={size}
      viewBox="-2 -2 28 28"
      fill="none"
      style={{
        flexShrink: 0,
        transformBox: 'view-box',
        transformOrigin: 'center',
        animation: spin ? 'days-daisy-spin 9s var(--ease-soft) infinite' : undefined,
        ...style,
      }}
    >
      <g fill={petalFill} stroke={petalStroke} strokeWidth="0.6">
        <path d={petal} />
        <path d={petal} transform="rotate(60 12 12)" />
        <path d={petal} transform="rotate(120 12 12)" />
        <path d={petal} transform="rotate(180 12 12)" />
        <path d={petal} transform="rotate(240 12 12)" />
        <path d={petal} transform="rotate(300 12 12)" />
      </g>
      <circle cx="12" cy="12" r="4.4" fill={centerFill} stroke={centerStroke} strokeWidth="0.5" />
    </svg>
  )
}

interface LogoProps {
  size?: number
  color?: string
}

export function Logo({ size = 32, color = 'var(--ink-coffee)' }: LogoProps) {
  const daisySize = size * 0.48
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 1,
        fontFamily: 'var(--font-serif)',
        fontStyle: 'italic',
        fontWeight: 500,
        fontSize: size,
        letterSpacing: '-0.02em',
        color,
        lineHeight: 1,
      }}
    >
      <span>days</span>
      <Daisy size={daisySize} style={{ transform: `translateY(${daisySize * 0.1}px)` }} />
    </div>
  )
}
