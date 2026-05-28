import { useEffect, useId } from "react";
import { type ScheduleItem } from "../../lib/week";
import { Icon } from "../days/Icon";

interface Props {
  open: boolean;
  onClose: () => void;
  schedules: ScheduleItem[];
  weekLabel: string;
  onScheduleClick: (s: ScheduleItem) => void;
}

export function WeekSchedulesModal({
  open,
  onClose,
  schedules,
  weekLabel,
  onScheduleClick,
}: Props) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(30,28,24,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 16px",
        zIndex: 9999,
        animation: "days-fade-in 200ms var(--ease-out) both",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 440,
          background: "var(--paper-pure)",
          border: "1px solid var(--line)",
          borderRadius: 24,
          boxShadow: "var(--shadow-3)",
          padding: "28px 28px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          animation: "days-pop 300ms var(--ease-soft) both",
        }}
      >
        {/* 헤더 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <h2
            id={titleId}
            style={{
              margin: 0,
              font: "600 17px/1.2 var(--font-sans)",
              color: "var(--ink-deep)",
              letterSpacing: "-0.01em",
            }}
          >
            {weekLabel} 일정
          </h2>
          <button
            aria-label="닫기"
            onClick={onClose}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: 999,
              border: "1px solid var(--line)",
              background: "var(--paper-bone)",
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            <Icon name="close" size={15} color="var(--ink-meta)" />
          </button>
        </div>

        {/* 일정 카드 리스트 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {schedules.map((s) => (
            <button
              key={s.id}
              onClick={() => {
                onScheduleClick(s);
                onClose();
              }}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 4,
                padding: "12px 16px",
                borderRadius: 12,
                border: "1px solid var(--line)",
                background: "var(--paper-bone)",
                cursor: "pointer",
                textAlign: "left",
                transition: "background var(--dur-1) var(--ease-out)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  "var(--sage-wash)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  "var(--paper-bone)";
              }}
            >
              <span
                style={{
                  font: "500 14px/1.3 var(--font-sans)",
                  color: "var(--ink-deep)",
                }}
              >
                {s.situation}
              </span>
              <span
                style={{
                  font: "400 12px/1.4 var(--font-sans)",
                  color: "var(--ink-hint)",
                }}
              >
                {s.period_start}
                {s.period_start !== s.period_end ? ` ~ ${s.period_end}` : ""}
              </span>
            </button>
          ))}
          {schedules.length === 0 && (
            <p
              style={{
                margin: 0,
                font: "400 14px/1.5 var(--font-sans)",
                color: "var(--ink-hint)",
                textAlign: "center",
                padding: "16px 0",
              }}
            >
              일정이 없습니다.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
