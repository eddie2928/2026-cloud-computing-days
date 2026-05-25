import { useEffect, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ open, onClose, children }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "white",
          borderRadius: 12,
          padding: 24,
          maxWidth: 640,
          width: "90%",
          maxHeight: "85vh",
          overflowY: "auto",
          position: "relative",
          animation: "days-pop 300ms var(--ease-soft) both",
        }}
      >
        <button
          onClick={onClose}
          aria-label="닫기"
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            background: "none",
            border: "none",
            fontSize: 20,
            cursor: "pointer",
            color: "var(--ink-meta)",
            lineHeight: 1,
            padding: "4px 8px",
          }}
        >
          ✕
        </button>
        {children}
      </div>
    </div>
  );
}
