interface ProgressBarProps {
  value: number;
  max?: number;
}

export function ProgressBar({ value, max = 5 }: ProgressBarProps) {
  return (
    <div style={{
      height: 6,
      background: 'var(--sage-cloud)',
      borderRadius: 'var(--r-pill)',
      overflow: 'hidden',
    }}>
      <div style={{
        width: `${(value / max) * 100}%`,
        height: '100%',
        background: 'var(--sage-leaf)',
        borderRadius: 'var(--r-pill)',
        transition: 'width var(--dur-3) var(--ease-out)',
      }} />
    </div>
  );
}
