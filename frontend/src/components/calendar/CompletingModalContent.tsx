import { useEffect } from 'react'

interface CompletingModalContentProps {
  onDone: () => void
  durationMs?: number
}

export function CompletingModalContent({ onDone, durationMs = 1500 }: CompletingModalContentProps) {
  useEffect(() => {
    const id = setTimeout(onDone, durationMs)
    return () => clearTimeout(id)
  }, [onDone, durationMs])

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        padding: '64px 24px',
        textAlign: 'center',
        animation: 'days-fade-in 400ms var(--ease-out) both',
      }}
    >
      <span style={{ fontSize: 40 }} aria-hidden>✨</span>
      <p
        style={{
          margin: 0,
          fontFamily: 'var(--font-sans)',
          fontWeight: 700,
          fontSize: 'var(--t-lg)',
          color: 'var(--sage-ink)',
          letterSpacing: '-0.01em',
        }}
      >
        일기가 완성되었어요
      </p>
      <p
        style={{
          margin: 0,
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--t-sm)',
          color: 'var(--ink-meta)',
        }}
      >
        잠시만 기다려 주세요...
      </p>
    </div>
  )
}
