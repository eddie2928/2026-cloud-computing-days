import { type ReactNode, useState, type CSSProperties } from 'react';

type Variant = 'primary' | 'ghost' | 'danger' | 'save';

interface PillButtonProps {
  children?: ReactNode;
  onClick?: () => void;
  variant?: Variant;
  disabled?: boolean;
  full?: boolean;
  style?: CSSProperties;
  icon?: ReactNode;
  type?: 'button' | 'submit' | 'reset';
}

export function PillButton({ children, onClick, variant = 'primary', disabled, full = true, style, icon, type = 'button' }: PillButtonProps) {
  const [pressed, setPressed] = useState(false);
  const [hover, setHover] = useState(false);

  const base: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '14px 24px',
    borderRadius: 'var(--r-pill)',
    border: 'none',
    fontFamily: 'var(--font-sans)',
    fontWeight: 600,
    fontSize: 'var(--t-base)',
    width: full ? '100%' : 'auto',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background var(--dur-1) var(--ease-out), transform var(--dur-1) var(--ease-soft), box-shadow var(--dur-1)',
    boxShadow: 'var(--shadow-card)',
    opacity: disabled ? 0.6 : 1,
  };

  const variants: Record<Variant, CSSProperties> = {
    primary: { background: disabled ? 'var(--sage-mist)' : 'var(--sage-leaf)', color: 'var(--paper-pure)' },
    ghost: { background: 'var(--paper-pure)', color: 'var(--ink-deep)', border: '1px solid var(--line)', boxShadow: 'var(--shadow-1)' },
    danger: { background: 'transparent', color: 'var(--accent-clay)', boxShadow: 'none' },
    save: { background: 'var(--sage-fern)', color: 'var(--paper-pure)' },
  };

  const hoverStyle: CSSProperties =
    hover && !disabled && variant === 'primary' ? { background: 'var(--sage-forest)' } :
    hover && !disabled && variant === 'ghost' ? { background: 'var(--paper-mist)' } : {};

  const pressStyle: CSSProperties = pressed && !disabled ? { transform: 'scale(0.97)', boxShadow: 'var(--shadow-press)' } : {};

  return (
    <button
      type={type}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPressed(false); }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      style={{ ...base, ...variants[variant], ...hoverStyle, ...pressStyle, ...style }}
    >
      {icon}
      {children}
    </button>
  );
}
