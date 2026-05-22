interface WordmarkProps {
  size?: number;
  color?: string;
}

export function Wordmark({ size = 36, color = 'var(--sage-ink)' }: WordmarkProps) {
  return (
    <span style={{
      fontFamily: 'var(--font-display)',
      fontWeight: 800,
      fontSize: size,
      letterSpacing: '-0.04em',
      color,
      lineHeight: 1,
    }}>Days</span>
  );
}
