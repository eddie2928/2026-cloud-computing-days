interface SuggestionChipsProps {
  suggestions: string[];
  onPick: (text: string) => void;
  disabled?: boolean;
}

export function SuggestionChips({ suggestions, onPick, disabled }: SuggestionChipsProps) {
  if (!suggestions.length) return null;

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        padding: '4px 0 8px',
        animation: 'days-rise 240ms var(--ease-out) both',
      }}
    >
      {suggestions.map((text, i) => (
        <button
          key={i}
          type="button"
          onClick={() => !disabled && onPick(text)}
          disabled={disabled}
          style={{
            padding: '8px 14px',
            borderRadius: 999,
            border: '1.5px solid var(--line)',
            background: 'var(--sage-mist)',
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--t-sm)',
            color: 'var(--ink-body)',
            cursor: disabled ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.5 : 1,
            transition: 'background var(--dur-1) var(--ease-out), opacity var(--dur-1)',
            animation: `days-rise 240ms var(--ease-out) ${i * 60}ms both`,
          }}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
