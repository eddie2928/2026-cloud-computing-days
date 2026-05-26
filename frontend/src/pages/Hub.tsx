import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import { WeekStrip } from "../components/hub/WeekStrip";
import { TodayDiaryCard } from "../components/hub/TodayDiaryCard";
import { SearchTriggerCard } from "../components/hub/SearchTriggerCard";
import { PetCard } from "../components/hub/PetCard";
import { getWeekWindow, type CalendarEntry } from "../lib/week";
import { fetchStreak } from "../lib/streak";
import { useMockDate } from "../hooks/useMockDate";

export function Hub() {
  const navigate = useNavigate();
  const today = useMockDate();
  const thisMonth = today.slice(0, 7);
  const [entries, setEntries] = useState<CalendarEntry[]>([]);
  const [diaryBody, setDiaryBody] = useState<string | null>(null);
  const [streak, setStreak] = useState<number | null>(null);

  useEffect(() => {
    client
      .get(`/calendar?month=${thisMonth}`)
      .then((res) => {
        setEntries(res.data.entries ?? []);
      })
      .catch(() => {});
  }, [thisMonth]);

  useEffect(() => {
    client
      .get(`/diary/${today}`)
      .then((res) => {
        setDiaryBody(res.data.body ?? "");
      })
      .catch(() => {
        setDiaryBody(null);
      });
  }, [today]);

  useEffect(() => {
    fetchStreak()
      .then(setStreak)
      .catch(() => setStreak(null));
  }, []);

  const weekDays = getWeekWindow(entries, today);
  const hasDiary = diaryBody !== null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        padding: "16px 16px 8px",
      }}
    >
      {streak !== null && streak > 0 && (
        <div
          style={{
            textAlign: "center",
            fontSize: "1.1rem",
            fontWeight: 600,
            color: "var(--sage-leaf)",
            animation: "days-pop 380ms var(--ease-soft) both",
          }}
        >
          🔥 {streak}일 연속
        </div>
      )}
      <div style={{ animation: "days-rise 320ms var(--ease-out) 40ms both" }}>
        <WeekStrip days={weekDays} today={today} />
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "stretch",
          animation: "days-rise 320ms var(--ease-out) 120ms both",
        }}
      >
        <TodayDiaryCard
          today={today}
          hasDiary={hasDiary}
          summary={diaryBody ?? undefined}
          onOpen={(date) => navigate(`/diary/${date}`)}
          onStart={() => navigate(`/qna/${today}`)}
        />
        <SearchTriggerCard onClick={() => navigate('/search')} />
      </div>

      <div style={{ animation: "days-rise 320ms var(--ease-out) 200ms both" }}>
        <PetCard />
      </div>
    </div>
  );
}
