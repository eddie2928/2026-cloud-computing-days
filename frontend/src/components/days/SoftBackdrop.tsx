type BackdropVariant = 'login' | 'app';

interface SoftBackdropProps {
  variant?: BackdropVariant;
}

const blobBase = {
  position: 'absolute' as const,
  borderRadius: '50%',
  filter: 'blur(48px)',
  pointerEvents: 'none' as const,
  zIndex: 0,
};

export function SoftBackdrop({ variant = 'app' }: SoftBackdropProps) {
  if (variant === 'login') {
    return (
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
        <div style={{ ...blobBase, width: 320, height: 240, background: 'var(--cloud-1)', top: -60, left: -80 }} />
        <div style={{ ...blobBase, width: 240, height: 200, background: 'var(--cloud-2)', top: '40%', left: '30%' }} />
        <div style={{ ...blobBase, width: 200, height: 180, background: 'var(--cloud-3)', bottom: -40, right: -60 }} />
      </div>
    );
  }
  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
      <div style={{ ...blobBase, width: 200, height: 160, background: 'var(--sage-wash)', bottom: 60, left: -40 }} />
      <div style={{ ...blobBase, width: 160, height: 140, background: 'var(--cloud-1)', top: 40, right: -40 }} />
    </div>
  );
}
