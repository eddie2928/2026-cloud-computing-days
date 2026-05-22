import { type ReactNode } from 'react';

interface FieldLabelProps {
  children: ReactNode;
  required?: boolean;
}

export function FieldLabel({ children, required }: FieldLabelProps) {
  return (
    <label className="t-label" style={{ display: 'block', marginBottom: 8, fontWeight: 600 }}>
      {children}
      {required && <span style={{ color: 'var(--accent-clay)', fontWeight: 500, marginLeft: 4 }}>*</span>}
    </label>
  );
}
