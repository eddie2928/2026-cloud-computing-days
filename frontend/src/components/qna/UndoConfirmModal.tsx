interface UndoConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (mode: 'keep' | 'discard') => void;
  targetSequence: number;
}

export function UndoConfirmModal({ open, onClose, onConfirm, targetSequence }: UndoConfirmModalProps) {
  if (!open) return null;

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  };

  return (
    <div
      role="presentation"
      onClick={onClose}
      onKeyDown={handleKey}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(30,28,24,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px',
        zIndex: 9999,
        animation: 'days-fade-in 200ms var(--ease-out) both',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="undo-modal-title"
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 440,
          background: 'var(--paper-pure)',
          border: '1px solid var(--line)',
          borderRadius: 24,
          boxShadow: 'var(--shadow-3)',
          padding: '28px 28px 24px',
          animation: 'days-pop 300ms var(--ease-soft) both',
        }}
      >
        <h2
          id="undo-modal-title"
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '18px',
            fontWeight: 600,
            color: 'var(--ink-deep)',
            margin: '0 0 8px',
            letterSpacing: '-0.01em',
          }}
        >
          {targetSequence}번째 답변을 수정할게요
        </h2>
        <p
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '14px',
            color: 'var(--ink-meta)',
            margin: '0 0 24px',
            lineHeight: 1.6,
          }}
        >
          어떻게 수정할까요?
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <button
            type="button"
            onClick={() => onConfirm('keep')}
            style={{
              padding: '13px 20px',
              borderRadius: 999,
              border: '1.5px solid var(--sage-leaf)',
              background: 'transparent',
              fontFamily: 'var(--font-sans)',
              fontSize: '15px',
              fontWeight: 500,
              color: 'var(--sage-forest)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background var(--dur-1) var(--ease-out)',
            }}
          >
            이 답변 수정하기
            <span style={{ display: 'block', fontSize: '12px', color: 'var(--ink-hint)', fontWeight: 400, marginTop: 2 }}>
              질문은 그대로 두고 답변 텍스트만 고칩니다
            </span>
          </button>
          <button
            type="button"
            onClick={() => onConfirm('discard')}
            style={{
              padding: '13px 20px',
              borderRadius: 999,
              border: 0,
              background: 'var(--sage-leaf)',
              fontFamily: 'var(--font-sans)',
              fontSize: '15px',
              fontWeight: 600,
              color: 'var(--paper-pure)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background var(--dur-1) var(--ease-out)',
            }}
          >
            이후 기록 삭제하고 다시
            <span style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.7)', fontWeight: 400, marginTop: 2 }}>
              이 질문부터 다시 답합니다. 이후 대화·추출 일정 삭제
            </span>
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '11px',
              borderRadius: 999,
              border: 0,
              background: 'transparent',
              fontFamily: 'var(--font-sans)',
              fontSize: '14px',
              color: 'var(--ink-hint)',
              cursor: 'pointer',
              transition: 'color var(--dur-1)',
            }}
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
