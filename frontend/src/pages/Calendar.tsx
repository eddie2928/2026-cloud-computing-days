import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import client from "../api/client";
import { listPlansForCalendar } from "../api/plans";
import { MonthGrid } from "../components/calendar/MonthGrid";
import {
  type CalendarEntry,
  type HolidayItem,
  type ScheduleItem,
} from "../lib/week";
import type { PlanWithTodosOut } from "../lib/plans";
import { getSeoulToday } from "../lib/today";

const [initYear, initMonth] = getSeoulToday().split('-').map(Number);

export function Calendar() {
  const navigate = useNavigate();
  const [year, setYear] = useState(initYear);
  const [month, setMonth] = useState(initMonth);
  const [direction, setDirection] = useState<"left" | "right">("left");
  const [entries, setEntries] = useState<CalendarEntry[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [holidays, setHolidays] = useState<HolidayItem[]>([]);
  const [plans, setPlans] = useState<PlanWithTodosOut[]>([]);
  const [searchParams, setSearchParams] = useSearchParams();
  const view: "schedule" | "plan" = searchParams.get("view") === "plan" ? "plan" : "schedule";

  const fetchCalendar = useCallback(() => {
    const m = `${year}-${String(month).padStart(2, "0")}`;
    client
      .get(`/calendar?month=${m}`)
      .then((res) => {
        setEntries(res.data.entries ?? []);
        setSchedules(res.data.schedules ?? []);
        setHolidays(res.data.holidays ?? []);
      })
      .catch(() => {});
  }, [year, month]);

  const fetchPlans = useCallback(() => {
    const daysInMonth = new Date(year, month, 0).getDate();
    const monthStart = `${year}-${String(month).padStart(2, "0")}-01`;
    const monthEnd = `${year}-${String(month).padStart(2, "0")}-${String(daysInMonth).padStart(2, "0")}`;
    listPlansForCalendar(monthStart, monthEnd)
      .then(setPlans)
      .catch(() => setPlans([]));
  }, [year, month]);

  useEffect(() => {
    fetchCalendar();
  }, [fetchCalendar]);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const goPrev = () => {
    setDirection("left");
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else setMonth((m) => m - 1);
  };

  const goNext = () => {
    setDirection("right");
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else setMonth((m) => m + 1);
  };

  return (
    <div style={{ padding: "8px 16px" }}>
      {/* 일정 / 플랜 버전 토글 */}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 4, marginBottom: 4 }}>
        {(["schedule", "plan"] as const).map((v) => (
          <button
            key={v}
            onClick={() =>
              v === "plan"
                ? setSearchParams({ view: "plan" }, { replace: true })
                : setSearchParams({}, { replace: true })
            }
            style={{
              padding: "3px 10px",
              border: "1px solid var(--line)",
              borderRadius: "var(--r-pill)",
              cursor: "pointer",
              font: "500 11px/1 var(--font-sans)",
              background: view === v ? "var(--sage-leaf)" : "transparent",
              color: view === v ? "var(--paper-pure)" : "var(--ink-hint)",
            }}
          >
            {v === "schedule" ? "일정" : "플랜"}
          </button>
        ))}
      </div>
      <MonthGrid
        year={year}
        month={month}
        direction={direction}
        entries={entries}
        schedules={schedules}
        holidays={holidays}
        plans={plans}
        mode={view}
        onPrev={goPrev}
        onNext={goNext}
        onCellClick={(date) => {
          if (entries.some((e) => e.date === date)) navigate(`/diary/${date}`);
          else navigate(`/qna/${date}`);
        }}
        onScheduleClick={(s) => navigate(`/schedule/${s.id}`)}
        onPlanDayClick={(planId, date) => navigate(`/plans/${planId}/day/${date}`)}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: 12,
          marginBottom: 8,
        }}
      >
        <button
          onClick={() =>
            navigate(
              view === "schedule" ? "/schedule/new" : "/plans/new",
              { state: { from: `/calendar?view=${view}` } }
            )
          }
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "9px 20px",
            borderRadius: 999,
            border: "1.5px solid var(--sage-leaf)",
            background: "transparent",
            color: "var(--sage-forest)",
            fontFamily: "var(--font-sans)",
            fontWeight: 500,
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          <span style={{ fontSize: 16, lineHeight: 1 }}>+</span>
          {view === "schedule" ? "일정 추가" : "플랜 추가"}
        </button>
      </div>
    </div>
  );
}
