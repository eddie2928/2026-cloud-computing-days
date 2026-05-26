/* global React */
const { useState, useRef, useEffect } = React;

/* ────────────────────────────────────────────────────────────────────
 * Logo — the cloud-leaf mark + Days wordmark
 * ──────────────────────────────────────────────────────────────────── */
function CloudLeaf({ size = 40, color = 'var(--sage-forest)', stroke = 3 }) {
  // Clean cloud outline matching the live app logo. (Name kept for API
  // back-compat; the inner leaf shape from earlier drafts was removed.)
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <path
        d="M15 41 C9 41 5 36.8 5 31.4 C5 26.4 8.8 22.4 13.8 22.1 C15 17.5 19.4 14 24.6 14 C28.8 14 32.4 16.2 34.2 19.4 C35.8 18.6 37.6 18.2 39.4 18.2 C44.8 18.2 49.2 22.2 49.6 27.2 C53.6 27.6 57 30.8 57 34.6 C57 38.8 53.4 41 49 41 Z"
        stroke={color} strokeWidth={stroke} strokeLinejoin="round" strokeLinecap="round" fill="none"
      />
    </svg>
  );
}

function Wordmark({ size = 36, color = 'var(--sage-ink)' }) {
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

function Logo({ size = 36, gap = 8, mark = true, color = 'var(--sage-ink)', markColor = 'var(--sage-forest)' }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap }}>
      {mark && <CloudLeaf size={size * 0.85} color={markColor} />}
      <Wordmark size={size} color={color} />
    </span>
  );
}

/* ────────────────────────────────────────────────────────────────────
 * Icon — inline SVG paths, single colour via currentColor
 * ──────────────────────────────────────────────────────────────────── */
const ICON_PATHS = {
  user: <><circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.5 3.1-6 7-6s7 2.5 7 6"/></>,
  lock: <><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></>,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></>,
  camera: <><path d="M3 8h3l2-2h8l2 2h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/></>,
  bell: <><path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2H4.5z"/><path d="M10 20a2 2 0 0 0 4 0"/></>,
  cake: <><rect x="4" y="12" width="16" height="8" rx="1.5"/><path d="M4 16c2 1.5 4 1.5 6 0s4 1.5 6 0 2 1.5 4 0"/><path d="M9 8v2M12 7v3M15 8v2"/><circle cx="9" cy="6.5" r="0.7" fill="currentColor"/><circle cx="12" cy="5.5" r="0.7" fill="currentColor"/><circle cx="15" cy="6.5" r="0.7" fill="currentColor"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 14.6a1.7 1.7 0 0 0 .4 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.4 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .4-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.4-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.4h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.9-.4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.4 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></>,
  'chevron-left': <path d="M15 6l-6 6 6 6"/>,
  'chevron-right': <path d="M9 6l6 6-6 6"/>,
  'arrow-left': <><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></>,
  'arrow-right': <><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></>,
  'arrow-up': <><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  close: <path d="M6 6l12 12M18 6L6 18"/>,
  check: <path d="M4 12l5 5L20 6"/>,
  pencil: <><path d="M14 4l6 6L9 21l-7 1 1-7z"/><path d="M14 4l4 4"/></>,
  cloud: <path d="M7 18h11a4 4 0 1 0-1-7.9 6 6 0 0 0-11.5 1.4A3.5 3.5 0 0 0 7 18z"/>,
  calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></>,
  book: <><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19a2 2 0 0 1 2-2h13"/></>,
  sparkles: <><path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z"/><path d="M19 16l.7 1.8L21.5 18.5l-1.8.7L19 21l-.7-1.8L16.5 18.5l1.8-.7z"/></>,
};

function Icon({ name, size = 20, color = 'currentColor', stroke = 1.75, style }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
         aria-label={name} role="img"
         style={{ flexShrink: 0, ...style }}>
      {ICON_PATHS[name] || null}
    </svg>
  );
}

/* ────────────────────────────────────────────────────────────────────
 * PhoneFrame — the 390×844 rounded device sitting on the sage backdrop
 * ──────────────────────────────────────────────────────────────────── */
function PhoneFrame({ children, label }) {
  return (
    <div className="phone-outer">
      {label && <div className="phone-label">{label}</div>}
      <div className="phone">
        <div className="phone-bezel">
          <div className="phone-notch" />
          <div className="phone-screen">{children}</div>
        </div>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────
 * Primitives
 * ──────────────────────────────────────────────────────────────────── */

function PillButton({ children, onClick, variant = 'primary', disabled, full = true, style, icon, type = 'button' }) {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '14px 24px',
    borderRadius: 'var(--r-pill)',
    border: 0,
    fontFamily: 'var(--font-sans)',
    fontWeight: 600,
    fontSize: 'var(--t-base)',
    width: full ? '100%' : 'auto',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background var(--dur-1) var(--ease-out), transform var(--dur-1) var(--ease-soft), box-shadow var(--dur-1)',
    boxShadow: 'var(--shadow-card)',
  };
  const variants = {
    primary: {
      background: disabled ? 'var(--sage-mist)' : 'var(--sage-leaf)',
      color: 'var(--paper-pure)',
    },
    ghost: {
      background: 'var(--paper-pure)',
      color: 'var(--ink-deep)',
      border: '1px solid var(--line)',
      boxShadow: 'var(--shadow-1)',
    },
    danger: {
      background: 'transparent',
      color: 'var(--accent-clay)',
      boxShadow: 'none',
    },
    save: {
      background: 'var(--sage-fern)',
      color: 'var(--paper-pure)',
    },
  };
  const [pressed, setPressed] = useState(false);
  const [hover, setHover] = useState(false);

  return (
    <button
      type={type}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setPressed(false); }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      style={{
        ...base,
        ...variants[variant],
        ...(hover && !disabled && variant === 'primary' ? { background: 'var(--sage-forest)' } : {}),
        ...(hover && !disabled && variant === 'ghost' ? { background: 'var(--paper-mist)' } : {}),
        ...(pressed && !disabled ? { transform: 'scale(0.97)', boxShadow: 'var(--shadow-press)' } : {}),
        opacity: disabled ? 0.6 : 1,
        ...style,
      }}
    >
      {icon}
      {children}
    </button>
  );
}

function PillInput({ value, onChange, placeholder, type = 'text', icon, ariaLabel }) {
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
      {icon && <span style={{ color: 'var(--ink-meta)' }}>{icon}</span>}
      <input
        type={type}
        value={value}
        onChange={onChange}
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

function BoxInput({ value, onChange, placeholder, type = 'text', icon, ariaLabel, suffix }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '12px 16px',
      background: 'var(--paper-pure)',
      borderRadius: 'var(--r-4)',
      border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
      boxShadow: focused ? 'var(--shadow-ring)' : 'var(--shadow-1)',
      transition: 'border-color var(--dur-1), box-shadow var(--dur-1)',
    }}>
      {icon && <span style={{ color: 'var(--ink-meta)', display: 'flex' }}>{icon}</span>}
      <input
        type={type}
        value={value}
        onChange={onChange}
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
      {suffix && <span style={{ color: 'var(--ink-meta)', display: 'flex' }}>{suffix}</span>}
    </div>
  );
}

function Chip({ children, active, onClick, variant = 'pill', icon }) {
  if (variant === 'segment') {
    return (
      <button
        onClick={onClick}
        style={{
          flex: 1,
          padding: '14px 8px',
          borderRadius: 'var(--r-pill)',
          border: active ? '0' : '1.5px solid var(--line)',
          background: active ? 'var(--sage-leaf)' : 'var(--paper-pure)',
          color: active ? 'var(--paper-pure)' : 'var(--ink-body)',
          fontFamily: 'var(--font-sans)',
          fontWeight: 500,
          fontSize: 'var(--t-base)',
          cursor: 'pointer',
          boxShadow: active ? 'var(--shadow-card)' : 'none',
          transition: 'background var(--dur-1), color var(--dur-1)',
        }}
      >{children}</button>
    );
  }
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '8px 14px',
        borderRadius: 'var(--r-pill)',
        border: active ? '0' : '1.5px solid var(--line)',
        background: active ? 'var(--sage-leaf)' : 'var(--paper-pure)',
        color: active ? 'var(--paper-pure)' : 'var(--ink-body)',
        fontFamily: 'var(--font-sans)',
        fontWeight: 500,
        fontSize: 'var(--t-sm)',
        cursor: 'pointer',
        transition: 'background var(--dur-1), color var(--dur-1)',
      }}
    >{icon}{children}</button>
  );
}

function FieldLabel({ children, required }) {
  return (
    <label className="t-label" style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
      {children}
      {required && <span className="t-required" style={{ marginLeft: 4 }}>*</span>}
    </label>
  );
}

function ProgressBar({ value, max = 5 }) {
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

/* ────────────────────────────────────────────────────────────────────
 * Decorative — soft drifting cloud / leaf blobs behind the screen
 * ──────────────────────────────────────────────────────────────────── */
function SoftBackdrop({ variant = 'login' }) {
  // Static SVG ellipses positioned absolutely behind everything in the screen.
  if (variant === 'login') {
    return (
      <div className="backdrop">
        <div className="blob blob-tl" />
        <div className="blob blob-mid" />
        <div className="blob blob-br" />
        <div className="cloud cloud-tr" />
        <div className="cloud cloud-bl" />
      </div>
    );
  }
  return (
    <div className="backdrop">
      <div className="blob blob-bl-sm" />
      <div className="blob blob-tr-sm" />
    </div>
  );
}

window.DaysUI = {
  React, useState, useRef, useEffect,
  CloudLeaf, Wordmark, Logo, Icon, PhoneFrame,
  PillButton, PillInput, BoxInput, Chip, FieldLabel, ProgressBar,
  SoftBackdrop,
};
