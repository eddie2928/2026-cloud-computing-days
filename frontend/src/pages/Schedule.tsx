import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { Header } from "../components/layout/Header";
import { type ScheduleItem } from "../lib/week";

export function Schedule() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState<ScheduleItem | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [mode, setMode] = useState<"view" | "edit" | "delete-confirm">("view");
  const [situation, setSituation] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    client
      .get(`/schedules/${id}`)
      .then((res) => {
        const s: ScheduleItem = res.data;
        setSchedule(s);
        setSituation(s.situation);
        setPeriodStart(s.period_start);
        setPeriodEnd(s.period_end);
        setStartTime(s.start_time ?? "");
        setEndTime(s.end_time ?? "");
      })
      .catch((e) => {
        if (e.response?.status === 404) setNotFound(true);
      });
  }, [id]);

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await client.patch(`/schedules/${id}`, {
        situation,
        period_start: periodStart,
        period_end: periodEnd,
        start_time: startTime || null,
        end_time: endTime || null,
      });
      navigate(-1);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await client.delete(`/schedules/${id}`);
      navigate(-1);
    } finally {
      setSaving(false);
    }
  };

  if (notFound) {
    return (
      <div style={{ display: "flex", flexDirection: "column" }}>
        <Header title="일정" showBack />
        <div
          style={{
            padding: 24,
            textAlign: "center",
            fontFamily: "var(--font-sans)",
            color: "var(--ink-hint)",
          }}
        >
          일정을 찾을 수 없어요.
        </div>
      </div>
    );
  }

  if (!schedule) {
    return (
      <div style={{ display: "flex", flexDirection: "column" }}>
        <Header title="일정" showBack />
        <div
          style={{
            padding: 24,
            fontFamily: "var(--font-sans)",
            color: "var(--ink-hint)",
          }}
        >
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <Header title="일정" showBack />

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
        {mode === "view" && (
          <>
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
              일정
            </p>
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 400,
                fontSize: 18,
                lineHeight: 1.3,
                color: "var(--ink-deep)",
                margin: "0 0 8px",
              }}
            >
              {schedule.situation}
            </p>
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 400,
                fontSize: 13,
                lineHeight: 1,
                color: "var(--ink-hint)",
                margin: "0 0 4px",
              }}
            >
              {schedule.period_start} ~ {schedule.period_end}
            </p>
            {(schedule.start_time || schedule.end_time) && (
              <p
                style={{
                  fontFamily: "var(--font-sans)",
                  fontWeight: 400,
                  fontSize: 13,
                  lineHeight: 1,
                  color: "var(--ink-hint)",
                  margin: "0 0 20px",
                }}
              >
                {schedule.start_time ?? ""}{schedule.start_time && schedule.end_time ? " – " : ""}{schedule.end_time ?? ""}
              </p>
            )}
            {!schedule.start_time && !schedule.end_time && (
              <div style={{ marginBottom: 20 }} />
            )}
            <hr
              style={{
                border: "none",
                borderTop: "1px solid var(--line-faint)",
                margin: "0 0 16px",
              }}
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setMode("edit")}
                style={{
                  flex: 1,
                  background: "var(--paper-pure)",
                  border: "1px solid var(--line)",
                  borderRadius: "var(--r-3, 12px)",
                  padding: "8px 0",
                  fontFamily: "var(--font-sans)",
                  fontWeight: 500,
                  fontSize: 14,
                  color: "var(--ink-body)",
                  cursor: "pointer",
                }}
              >
                수정
              </button>
              <button
                onClick={() => setMode("delete-confirm")}
                style={{
                  background: "transparent",
                  border: "none",
                  borderRadius: "var(--r-3, 12px)",
                  padding: "8px 16px",
                  fontFamily: "var(--font-sans)",
                  fontWeight: 500,
                  fontSize: 14,
                  color: "var(--accent-clay)",
                  cursor: "pointer",
                }}
              >
                삭제
              </button>
            </div>
          </>
        )}

        {mode === "edit" && (
          <>
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
              일정 수정
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
              <div style={{ display: "flex", gap: 8 }}>
                <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
                  <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                    시작 시간
                  </span>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
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
                <label style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
                  <span style={{ fontFamily: "var(--font-sans)", fontSize: 12, color: "var(--ink-meta)" }}>
                    종료 시간
                  </span>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
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
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleSave}
                disabled={saving}
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
                  cursor: saving ? "default" : "pointer",
                  opacity: saving ? 0.6 : 1,
                }}
              >
                저장
              </button>
              <button
                onClick={() => setMode("view")}
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
          </>
        )}

        {mode === "delete-confirm" && (
          <>
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontWeight: 500,
                fontSize: 11,
                lineHeight: 1,
                color: "var(--accent-clay)",
                margin: "0 0 12px",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              삭제 확인
            </p>
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: 14,
                color: "var(--ink-deep)",
                margin: "0 0 20px",
              }}
            >
              이 일정을 삭제합니다.
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleDelete}
                disabled={saving}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "1px solid var(--accent-clay)",
                  borderRadius: "var(--r-3, 12px)",
                  padding: "9px 0",
                  fontFamily: "var(--font-sans)",
                  fontWeight: 600,
                  fontSize: 14,
                  color: "var(--accent-clay)",
                  cursor: saving ? "default" : "pointer",
                  opacity: saving ? 0.6 : 1,
                }}
              >
                확인
              </button>
              <button
                onClick={() => setMode("view")}
                style={{
                  background: "transparent",
                  border: "none",
                  borderRadius: "var(--r-3, 12px)",
                  padding: "9px 16px",
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
          </>
        )}
      </div>
    </div>
  );
}
