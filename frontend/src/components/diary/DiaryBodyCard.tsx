interface DiaryBodyCardProps {
  body: string;
}

export function DiaryBodyCard({ body }: DiaryBodyCardProps) {
  return (
    <div style={{
      background: 'var(--paper-warm)',
      borderRadius: 'var(--r-5)',
      border: '1px solid var(--line-faint)',
      boxShadow: 'var(--shadow-2)',
      padding: '24px 20px',
    }}>
      <p style={{
        margin: 0,
        fontFamily: 'var(--font-sans)',
        fontSize: 'var(--t-md)',
        color: 'var(--sage-ink)',
        lineHeight: 1.85,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}>
        {body}
      </p>
    </div>
  );
}
