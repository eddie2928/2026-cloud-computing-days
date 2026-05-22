interface CloudLeafProps {
  size?: number;
  color?: string;
  stroke?: number;
}

export function CloudLeaf({ size = 40, color = 'var(--sage-forest)', stroke = 3 }: CloudLeafProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path
        d="M15 41 C9 41 5 36.8 5 31.4 C5 26.4 8.8 22.4 13.8 22.1 C15 17.5 19.4 14 24.6 14 C28.8 14 32.4 16.2 34.2 19.4 C35.8 18.6 37.6 18.2 39.4 18.2 C44.8 18.2 49.2 22.2 49.6 27.2 C53.6 27.6 57 30.8 57 34.6 C57 38.8 53.4 41 49 41 Z"
        stroke={color}
        strokeWidth={stroke}
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
