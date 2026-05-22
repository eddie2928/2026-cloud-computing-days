/* global React */
const daysPrim = {};

daysPrim.Eyebrow = function Eyebrow({ children, style }) {
  return <div style={{ font: '500 11px/1 var(--font-sans)', letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--gold-deep)', ...style }}>{children}</div>;
};

daysPrim.Icon = function Icon({ name, size = 20, color }) {
  return <img src={`../../assets/icons/${name}.svg`} alt="" width={size} height={size} style={{ display: 'block', filter: color ? undefined : undefined, opacity: 0.95 }}/>;
};

daysPrim.Button = function Button({ children, variant = 'primary', disabled, onClick, type = 'button', style }) {
  const baseStyles = {
    font: '600 15px/1 var(--font-sans)',
    letterSpacing: '-0.005em',
    border: 0,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background var(--dur-1) var(--ease-out), transform var(--dur-1) var(--ease-out), box-shadow var(--dur-1) var(--ease-out), border-color var(--dur-1)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    opacity: disabled ? 0.55 : 1,
  };
  const variants = {
    primary: {
      background: disabled ? 'var(--paper-warm)' : 'linear-gradient(180deg, var(--gold-warm), var(--gold))',
      color: disabled ? 'var(--ink-stone)' : '#fff',
      padding: '8px 14px 6px',
      borderRadius: 999,
      boxShadow: disabled ? 'none' : '0 2px 6px rgba(94,70,30,0.10)',
    },
    secondary: {
      background: 'var(--paper-cream)',
      color: 'var(--ink-walnut)',
      padding: '8px 12px 6px',
      borderRadius: 12,
      border: '1px solid var(--line)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--gold-deep)',
      padding: '8px 10px 6px',
      borderRadius: 12,
    },
  };
  return (
    <button
      type={type}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      onMouseDown={(e) => !disabled && (e.currentTarget.style.transform = 'scale(0.98)')}
      onMouseUp={(e) => !disabled && (e.currentTarget.style.transform = '')}
      onMouseLeave={(e) => !disabled && (e.currentTarget.style.transform = '')}
      style={{ ...baseStyles, ...variants[variant], ...style }}
    >
      {children}
    </button>
  );
};

daysPrim.fieldBase = {
  font: '400 15px/1.4 var(--font-sans)',
  width: '100%',
  boxSizing: 'border-box',
  padding: '8px 10px',
  background: 'var(--paper-mist)',
  border: '1px solid var(--line)',
  borderRadius: 12,
  color: 'var(--ink-coffee)',
  outline: 'none',
  transition: 'border-color var(--dur-1), box-shadow var(--dur-1), background var(--dur-1)',
  fontFamily: 'var(--font-sans)',
};

daysPrim.applyFocus = (e) => {
  e.currentTarget.style.borderColor = 'var(--gold)';
  e.currentTarget.style.boxShadow = '0 0 0 4px rgba(214,166,70,0.18)';
  e.currentTarget.style.background = 'var(--paper-bone)';
};
daysPrim.removeFocus = (e) => {
  e.currentTarget.style.borderColor = 'var(--line)';
  e.currentTarget.style.boxShadow = 'none';
  e.currentTarget.style.background = 'var(--paper-mist)';
};

daysPrim.TextField = function TextField({ label, type = 'text', value, onChange, placeholder, autoFocus }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && <label style={{ font: '500 12px/1 var(--font-sans)', color: 'var(--ink-bark)', letterSpacing: '0.04em' }}>{label}</label>}
      <input
        type={type}
        value={value}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={daysPrim.applyFocus}
        onBlur={daysPrim.removeFocus}
        style={daysPrim.fieldBase}
      />
    </div>
  );
};

daysPrim.DateField = function DateField({ label, value, onChange }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && <label style={{ font: '500 12px/1 var(--font-sans)', color: 'var(--ink-bark)', letterSpacing: '0.04em' }}>{label}</label>}
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={daysPrim.applyFocus}
        onBlur={daysPrim.removeFocus}
        style={{ ...daysPrim.fieldBase, fontFamily: 'var(--font-mono)', fontSize: 14 }}
      />
    </div>
  );
};

daysPrim.Textarea = function Textarea({ value, onChange, placeholder, onKeyDown, disabled, rows = 2, autoFocus }) {
  return (
    <textarea
      value={value}
      autoFocus={autoFocus}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      onKeyDown={onKeyDown}
      disabled={disabled}
      rows={rows}
      onFocus={daysPrim.applyFocus}
      onBlur={daysPrim.removeFocus}
      style={{
        ...daysPrim.fieldBase,
        resize: 'none',
        fontFamily: 'var(--font-sans)',
        opacity: disabled ? 0.6 : 1,
      }}
    />
  );
};

daysPrim.Card = function Card({ children, style }) {
  return (
    <div style={{
      background: 'var(--paper-cream)',
      border: '1px solid var(--line)',
      borderRadius: 18,
      padding: 24,
      boxShadow: '0 2px 6px rgba(94,70,30,0.08), 0 1px 2px rgba(94,70,30,0.04)',
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      ...style,
    }}>{children}</div>
  );
};

daysPrim.ThinkingDots = function ThinkingDots() {
  const dot = { width: 6, height: 6, borderRadius: 999, background: 'var(--gold-warm)' };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{ ...dot, animation: 'days-dot-pulse 1.2s var(--ease-out) infinite' }}/>
      <span style={{ ...dot, animation: 'days-dot-pulse 1.2s var(--ease-out) 0.18s infinite' }}/>
      <span style={{ ...dot, animation: 'days-dot-pulse 1.2s var(--ease-out) 0.36s infinite' }}/>
    </span>
  );
};

daysPrim.DotLeader = function DotLeader({ style }) {
  return <div style={{ height: 7, background: 'var(--dot-leader)', flex: 1, ...style }}/>;
};

window.daysPrim = daysPrim;
