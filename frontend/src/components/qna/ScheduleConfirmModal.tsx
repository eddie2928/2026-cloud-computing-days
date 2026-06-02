import { useState, useEffect } from "react";

export interface PendingScheduleItem {
  period_start: string;
  period_end: string;
  situation: string;
  start_time?: string | null;
  end_time?: string | null;
}

interface ScheduleConfirmModalProps {
  open: boolean;
  schedule: PendingScheduleItem | null;
  onAccept: (schedule: PendingScheduleItem & { start_time: string | null; end_time: string | null }) => void;
  onReject: () => void;
}

export function ScheduleConfirmModal({ open, schedule, onAccept, onReject }: ScheduleConfirmModalProps) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");

  useEffect(() => {
    if (schedule) {
      setStartDate(schedule.period_start);
      setEndDate(schedule.period_end);
      setStartTime(schedule.start_time || "09:00");
      setEndTime(schedule.end_time || "10:00");
    }
  }, [schedule]);

  if (!open || !schedule) return null;

  const isInvalidDate = endDate < startDate;

  const handleAccept = () => {
    if (isInvalidDate) return;
    onAccept({
      ...schedule,
      period_start: startDate,
      period_end: endDate,
      start_time: startTime || null,
      end_time: endTime || null,
    });
  };

  const inputStyle: React.CSSProperties = {
    background: "var(--paper-bone)",
    border: "1px solid var(--line)",
    borderRadius: 12,
    padding: "8px 12px",
    fontFamily: "var(--font-sans)",
    fontSize: 14,
    color: "var(--ink-deep)",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <div
      role="presentation"
      onClick={onReject}
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
        aria-labelledby="sched-modal-title"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 440,
          background: "var(--paper-pure)",
          border: "1px solid var(--line)",
          borderRadius: 24,
          boxShadow: "var(--shadow-3)",
          padding: "28px 28px 24px",
          animation: "days-pop 300ms var(--ease-soft) both",
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 500,
            fontSize: 11,
            lineHeight: 1,
            color: "var(--ink-meta)",
            margin: "0 0 10px",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          일정 추가
        </p>
        <h2
          id="sched-modal-title"
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 18,
            fontWeight: 600,
            color: "var(--ink-deep)",
            margin: "0 0 4px",
            letterSpacing: "-0.01em",
          }}
        >
          {schedule.situation}
        </h2>
        <div
          style={{
            borderTop: "1px solid var(--line-faint)",
            paddingTop: 16,
            marginBottom: 20,
          }}
        >
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: 12,
              color: "var(--ink-meta)",
              margin: "0 0 8px",
            }}
          >
            날짜 설정
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                시작일
              </span>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={inputStyle}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                종료일
              </span>
              <input
                type="date"
                value={endDate}
                min={startDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={inputStyle}
              />
            </label>
          </div>
          {isInvalidDate && (
            <p style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--accent-clay)", margin: "0 0 8px" }}>
              종료일은 시작일 이후여야 합니다.
            </p>
          )}
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: 12,
              color: "var(--ink-meta)",
              margin: "0 0 8px",
            }}
          >
            시간 설정 (선택)
          </p>
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                시작
              </span>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                style={inputStyle}
              />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                종료
              </span>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                style={inputStyle}
              />
            </label>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={handleAccept}
            disabled={isInvalidDate}
            style={{
              flex: 1,
              padding: "12px 20px",
              borderRadius: 999,
              border: 0,
              background: isInvalidDate ? "var(--line)" : "var(--sage-leaf)",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: 15,
              color: "var(--paper-pure)",
              cursor: isInvalidDate ? "not-allowed" : "pointer",
              boxShadow: isInvalidDate ? "none" : "var(--shadow-2)",
              transition: "background var(--dur-1) var(--ease-out)",
            }}
          >
            추가
          </button>
          <button
            type="button"
            onClick={onReject}
            style={{
              padding: "12px 20px",
              borderRadius: 999,
              border: 0,
              background: "transparent",
              fontFamily: "var(--font-sans)",
              fontWeight: 500,
              fontSize: 14,
              color: "var(--ink-meta)",
              cursor: "pointer",
              transition: "color var(--dur-1)",
            }}
          >
            무시
          </button>
        </div>
      </div>
    </div>
  );
}
