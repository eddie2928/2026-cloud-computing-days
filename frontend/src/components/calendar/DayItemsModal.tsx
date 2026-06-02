import type { ScheduleItem } from "../../lib/week";
import type { PlanWithTodosOut } from "../../lib/plans";
import { Icon } from "../days/Icon";

interface DayItemsModalProps {
  open: boolean;
  onClose: () => void;
  date: string;
  schedules: ScheduleItem[];
  plans: PlanWithTodosOut[];
  onScheduleClick?: (schedule: ScheduleItem) => void;
  onPlanDayClick?: (planId: number, date: string) => void;
}

export function DayItemsModal({
  open,
  onClose,
  date,
  schedules,
  plans,
  onScheduleClick,
  onPlanDayClick,
}: DayItemsModalProps) {
  if (!open) return null;

  const hasItems = schedules.length > 0 || plans.length > 0;

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
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 400,
          background: "var(--paper-pure)",
          border: "1px solid var(--line)",
          borderRadius: 24,
          boxShadow: "var(--shadow-3)",
          padding: "24px 24px 20px",
          animation: "days-pop 300ms var(--ease-soft) both",
        }}
      >
        {/* 헤더 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: 15,
              color: "var(--sage-ink)",
              letterSpacing: "-0.01em",
            }}
          >
            {date}
          </span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              color: "var(--ink-meta)",
              padding: 4,
            }}
          >
            <Icon name="close" size={18} />
          </button>
        </div>

        {/* 목록 */}
        {!hasItems ? (
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: 14,
              color: "var(--ink-hint)",
              textAlign: "center",
              padding: "16px 0",
            }}
          >
            일정이 없습니다.
          </p>
        ) : (
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: 6,
              maxHeight: 360,
              overflowY: "auto",
            }}
          >
            {schedules.map((s) => (
              <li key={`s-${s.id}`}>
                <button
                  onClick={() => {
                    onClose();
                    onScheduleClick?.(s);
                  }}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 12px",
                    background: "var(--sage-wash)",
                    border: "none",
                    borderRadius: 12,
                    cursor: onScheduleClick ? "pointer" : "default",
                    textAlign: "left",
                    transition: "background var(--dur-1) var(--ease-out)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      "var(--sage-mist)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background =
                      "var(--sage-wash)";
                  }}
                >
                  {s.start_time && (
                    <span
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--sage-forest)",
                        minWidth: 42,
                        flexShrink: 0,
                      }}
                    >
                      {s.start_time.slice(0, 5)}
                    </span>
                  )}
                  <span
                    style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--sage-ink)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {s.situation}
                  </span>
                </button>
              </li>
            ))}
            {plans.map((p) => (
              <li key={`p-${p.id}`}>
                <button
                  onClick={() => {
                    onClose();
                    onPlanDayClick?.(p.id, date);
                  }}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "10px 12px",
                    background: "var(--sage-leaf)",
                    opacity: 0.9,
                    border: "none",
                    borderRadius: 12,
                    cursor: onPlanDayClick ? "pointer" : "default",
                    textAlign: "left",
                    transition: "opacity var(--dur-1) var(--ease-out)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.opacity = "1";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.opacity = "0.9";
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: 11,
                      fontWeight: 600,
                      color: "var(--paper-pure)",
                      minWidth: 28,
                      flexShrink: 0,
                    }}
                  >
                    플랜
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--paper-pure)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {p.title}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
