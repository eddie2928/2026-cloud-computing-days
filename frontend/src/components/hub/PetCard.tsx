export function PetCard() {
  return (
    <div
      role="region"
      aria-label="다마고치 자리"
      style={{
        height: 120,
        borderRadius: 'var(--r-5)',
        border: '2px dashed var(--sage-mist)',
        background: 'rgba(255,255,255,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        padding: 16,
        color: 'var(--ink-meta)',
        font: '500 14px/1.4 var(--font-sans)',
      }}
    >
      <span style={{ fontSize: 28 }} aria-hidden>🥚</span>
      <span>다마고치가 곧 찾아와요</span>
    </div>
  )
}
