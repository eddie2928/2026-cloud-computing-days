import { useState, type KeyboardEvent } from 'react';
import { Icon } from '../days/Icon';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
  value?: string;
  onChange?: (v: string) => void;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder = '답변을 입력하세요...',
  value: valueProp,
  onChange,
}: ChatInputProps) {
  const [internalValue, setInternalValue] = useState('');
  const [focused, setFocused] = useState(false);

  const isControlled = valueProp !== undefined;
  const value = isControlled ? valueProp : internalValue;

  const handleChange = (v: string) => {
    if (isControlled) {
      onChange?.(v);
    } else {
      setInternalValue(v);
    }
  };

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    handleChange('');
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '10px 14px',
      background: 'var(--paper-pure)',
      borderRadius: 'var(--r-pill)',
      border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
      boxShadow: focused ? 'var(--shadow-ring)' : 'var(--shadow-1)',
      transition: 'border-color var(--dur-1), box-shadow var(--dur-1)',
    }}>
      <input
        type="text"
        value={value}
        onChange={e => handleChange(e.target.value)}
        onKeyDown={handleKey}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        disabled={disabled}
        aria-label="답변 입력"
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
      <button
        aria-label="전송"
        onClick={handleSend}
        disabled={!value.trim() || disabled}
        style={{
          background: value.trim() && !disabled ? 'var(--sage-leaf)' : 'var(--sage-mist)',
          border: 'none',
          borderRadius: '50%',
          width: 36,
          height: 36,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: value.trim() && !disabled ? 'pointer' : 'not-allowed',
          flexShrink: 0,
          transition: 'background var(--dur-1)',
        }}
      >
        <Icon name="arrow-up" size={18} color="var(--paper-pure)" />
      </button>
    </div>
  );
}
