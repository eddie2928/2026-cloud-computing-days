import { useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import { Header } from "../components/layout/Header";

export function ScheduleNew() {
  const navigate = useNavigate();
  const [situation, setSituation] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!situation || !periodStart || !periodEnd) return;
    setSaving(true);
    try {
      await client.post("/schedules", {
        situation,
        period_start: periodStart,
        period_end: periodEnd,
      });
      navigate(-1);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <Header title="일정 추가" showBack />

      <div
        style={{
          margin: 16,
          background: "var(--paper-pure)",
          border: "1px solid var(--line)",
          borderRadius: "var(--r-5, 24px)",
          boxShadow: "var(--shadow-3)",
          padding: 24,
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 500,
            fontSize: 11,
            lineHeight: 1,
            color: "var(--ink-meta)",
            margin: "0 0 16px",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          새 일정
        </p>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            marginBottom: 20,
          }}
        >
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 12,
                color: "var(--ink-meta)",
              }}
            >
              내용
            </span>
            <input
              value={situation}
              onChange={(e) => setSituation(e.target.value)}
              placeholder="일정 내용을 입력하세요"
              style={{
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
              }}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 12,
                color: "var(--ink-meta)",
              }}
            >
              시작일
            </span>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              style={{
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
              }}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 12,
                color: "var(--ink-meta)",
              }}
            >
              종료일
            </span>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              style={{
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
              }}
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={handleSave}
            disabled={saving || !situation || !periodStart || !periodEnd}
            style={{
              flex: 1,
              background: "var(--sage-leaf)",
              border: "none",
              borderRadius: "var(--r-pill, 999px)",
              padding: "10px 0",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: 14,
              color: "var(--paper-pure)",
              cursor: saving || !situation || !periodStart || !periodEnd ? "default" : "pointer",
              opacity: saving || !situation || !periodStart || !periodEnd ? 0.6 : 1,
            }}
          >
            저장
          </button>
          <button
            onClick={() => navigate(-1)}
            style={{
              background: "transparent",
              border: "none",
              borderRadius: "var(--r-3, 12px)",
              padding: "10px 16px",
              fontFamily: "var(--font-sans)",
              fontWeight: 500,
              fontSize: 14,
              color: "var(--ink-meta)",
              cursor: "pointer",
            }}
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
