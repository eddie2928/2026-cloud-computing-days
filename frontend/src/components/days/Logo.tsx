import { CloudLeaf } from './CloudLeaf';
import { Wordmark } from './Wordmark';

interface LogoProps {
  size?: number;
  gap?: number;
  mark?: boolean;
  color?: string;
  markColor?: string;
}

export function Logo({ size = 36, gap = 8, mark = true, color = 'var(--sage-ink)', markColor = 'var(--sage-forest)' }: LogoProps) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap }}>
      {mark && <CloudLeaf size={size * 0.85 * 1.5} color={markColor} />}
      <Wordmark size={size} color={color} />
    </span>
  );
}
