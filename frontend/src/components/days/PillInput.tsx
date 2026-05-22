import { useState, type ReactNode, type InputHTMLAttributes } from 'react';

interface PillInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  icon?: ReactNode;
  ariaLabel?: string;
}

export function PillInput({ value, onChange, placeholder, type = 'text', icon, ariaLabel, ...rest }: PillInputProps) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '12px 18px',
      background: 'var(--paper-pure)',
      borderRadius: 'var(--r-pill)',
      border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
      boxShadow: focused ? 'var(--shadow-ring)' : 'var(--shadow-1)',
      transition: 'border-color var(--dur-1), box-shadow var(--dur-1)',
    }}>
      {icon && <span style={{ color: 'var(--ink-meta)', display: 'flex' }}>{icon}</span>}
      <input
        {...rest}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          flex: 1,
          border: 0,
          outline: 0,
          background: 'transparent',
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--t-base)',
          color: 'var(--ink-deep)',
        }}
      />
    </div>
  );
}
