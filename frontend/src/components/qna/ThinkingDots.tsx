interface ThinkingDotsProps {
  visible: boolean;
}

export function ThinkingDots({ visible }: ThinkingDotsProps) {
  if (!visible) return null;
  return (
    <div style={{ display: 'flex', gap: 4, padding: '8px 4px', alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <span
          key={i}
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--sage-fern)',
            display: 'inline-block',
            animation: `days-thinking 1.2s ${i * 0.2}s infinite ease-in-out`,
          }}
        />
      ))}
    </div>
  );
}
