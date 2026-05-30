interface ProgressBarProps {
  /** 0–100 percentage */
  value: number;
}

export function ProgressBar({ value }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      style={{
        width: '100%',
        height: 8,
        background: 'var(--line)',
        borderRadius: 4,
        overflow: 'hidden',
      }}
    >
      <div
        data-testid="pb-fill"
        style={{
          width: `${clamped}%`,
          height: '100%',
          background: 'var(--sage-leaf)',
          borderRadius: 4,
          transition: 'width 360ms ease',
        }}
      />
    </div>
  );
}
