import { useState } from "react";
import {
  type CalendarEntry,
  type HolidayItem,
  type ScheduleItem,
} from "../../lib/week";
import type { PlanWithTodosOut } from "../../lib/plans";
import { MoodEmoji, type Mood } from "../days/MoodEmoji";
import { Icon } from "../days/Icon";
import { WeekSchedulesModal } from "./WeekSchedulesModal";

interface MonthGridProps {
  year: number;
  month: number;
  direction?: "left" | "right";
  entries: CalendarEntry[];
  schedules?: ScheduleItem[];
  holidays?: HolidayItem[];
  plans?: PlanWithTodosOut[];
  onPrev: () => void;
  onNext: () => void;
  onCellClick: (date: string) => void;
  onScheduleClick?: (schedule: ScheduleItem) => void;
  onPlanDayClick?: (planId: number, date: string) => void;
}

const DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];
const TODAY = new Date().toISOString().split("T")[0];

function truncateName(name: string, max: number): string {
  return name.length > max ? name.slice(0, max) + ".." : name;
}

function chunkCells<T>(cells: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < cells.length; i += size) {
    chunks.push(cells.slice(i, i + size));
  }
  return chunks;
}

interface ScheduleBar {
  schedule: ScheduleItem;
  colStart: number; // 1-indexed grid column start
  colEnd: number; // 1-indexed grid column end (exclusive)
  rowIndex: number; // stack offset for overlap
}

function getScheduleBars(
  cells: Array<{ date: string; inMonth: boolean }>,
  schedules: ScheduleItem[],
): ScheduleBar[][] {
  // Returns an array of bars per week row (6 rows max)
  const weeks: ScheduleBar[][] = Array.from({ length: 6 }, () => []);

  for (const schedule of schedules) {
    const startDate = schedule.period_start;
    const endDate = schedule.period_end;

    for (let weekIdx = 0; weekIdx < 6; weekIdx++) {
      const weekCells = cells.slice(weekIdx * 7, weekIdx * 7 + 7);
      const weekDates = weekCells.map((c) => c.date);

      const firstOverlap = weekDates.findIndex(
        (d) => d >= startDate && d <= endDate,
      );
      const lastOverlap = (() => {
        for (let i = 6; i >= 0; i--) {
          if (weekDates[i] >= startDate && weekDates[i] <= endDate) return i;
        }
        return -1;
      })();

      if (firstOverlap === -1) continue;

      // Find a row slot that doesn't overlap with existing bars
      const existingBars = weeks[weekIdx];
      let rowIndex = 0;
      while (
        existingBars.some(
          (b) =>
            b.rowIndex === rowIndex &&
            b.colStart <= lastOverlap + 1 &&
            b.colEnd > firstOverlap + 1,
        )
      ) {
        rowIndex++;
      }

      weeks[weekIdx].push({
        schedule,
        colStart: firstOverlap + 1,
        colEnd: lastOverlap + 2,
        rowIndex,
      });
    }
  }

  return weeks;
}

interface PlanDaySegment {
  plan: PlanWithTodosOut;
  colIndex: number; // 1-indexed column within the week
  date: string;
  isFirstInWeek: boolean;
}

interface PlanWeekRow {
  planRowIndex: number; // stack offset for multiple plans
  segments: PlanDaySegment[];
}

function getPlanWeekRows(
  cells: Array<{ date: string; inMonth: boolean }>,
  plans: PlanWithTodosOut[],
): PlanWeekRow[][] {
  const weeks: PlanWeekRow[][] = Array.from({ length: 6 }, () => []);

  for (const plan of plans) {
    for (let weekIdx = 0; weekIdx < 6; weekIdx++) {
      const weekCells = cells.slice(weekIdx * 7, weekIdx * 7 + 7);
      const overlapping = weekCells
        .map((c, i) => ({ ...c, colIndex: i + 1 }))
        .filter((c) => c.date >= plan.period_start && c.date <= plan.period_end);

      if (overlapping.length === 0) continue;

      const planRowIndex = weeks[weekIdx].length;
      weeks[weekIdx].push({
        planRowIndex,
        segments: overlapping.map((c, segIdx) => ({
          plan,
          colIndex: c.colIndex,
          date: c.date,
          isFirstInWeek: segIdx === 0,
        })),
      });
    }
  }

  return weeks;
}

export function MonthGrid({
  year,
  month,
  direction = "left",
  entries,
  schedules = [],
  holidays = [],
  plans = [],
  onPrev,
  onNext,
  onCellClick,
  onScheduleClick,
  onPlanDayClick,
}: MonthGridProps) {
  const [openWeekIdx, setOpenWeekIdx] = useState<number | null>(null);

  const holidayMap = new Map(holidays.map((h) => [h.date, h]));
  const entryMap = new Map(entries.map((e) => [e.date, e]));
  const firstDay = new Date(year, month - 1, 1);
  const startOffset = firstDay.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const daysInPrev = new Date(year, month - 1, 0).getDate();

  const cells: Array<{ date: string; inMonth: boolean }> = [];

  for (let i = startOffset - 1; i >= 0; i--) {
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevYear = month === 1 ? year - 1 : year;
    const d = daysInPrev - i;
    cells.push({
      date: `${prevYear}-${String(prevMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      inMonth: false,
    });
  }

  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({
      date: `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      inMonth: true,
    });
  }

  const remaining = 42 - cells.length;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  for (let d = 1; d <= remaining; d++) {
    cells.push({
      date: `${nextYear}-${String(nextMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      inMonth: false,
    });
  }

  const sortedSchedules = [...schedules].sort((a, b) => {
    const aMulti = a.period_end > a.period_start ? 0 : 1;
    const bMulti = b.period_end > b.period_start ? 0 : 1;
    if (aMulti !== bMulti) return aMulti - bMulti;
    const aTime = a.start_time ?? "";
    const bTime = b.start_time ?? "";
    if (!aTime && !bTime) return 0;
    if (!aTime) return 1;
    if (!bTime) return -1;
    return aTime.localeCompare(bTime);
  });
  const weekBars = getScheduleBars(cells, sortedSchedules);
  const planWeekRows = getPlanWeekRows(cells, plans);
  const weeks = chunkCells(cells, 7);

  return (
    <div>
      {/* 월 네비게이션 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 4px 16px",
        }}
      >
        <button
          aria-label="이전 달"
          onClick={onPrev}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            color: "var(--ink-body)",
            padding: 8,
          }}
        >
          <Icon name="chevron-left" size={20} />
        </button>
        <span
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 700,
            fontSize: "var(--t-md)",
            color: "var(--sage-ink)",
            letterSpacing: "-0.01em",
          }}
        >
          {year}.{String(month).padStart(2, "0")}
        </span>
        <button
          aria-label="다음 달"
          onClick={onNext}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            color: "var(--ink-body)",
            padding: 8,
          }}
        >
          <Icon name="chevron-right" size={20} />
        </button>
      </div>

      {/* 요일 헤더 */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          marginBottom: 4,
        }}
      >
        {DAY_LABELS.map((d) => (
          <div
            key={d}
            style={{
              textAlign: "center",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-xs)",
              color: "var(--cal-weekday-label, var(--ink-hint))",
              padding: "4px 0",
            }}
          >
            {d}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 — 주(week) 단위 행 */}
      <div style={{ overflow: "hidden" }}>
        <div
          key={`${year}-${month}`}
          data-testid="month-grid"
          style={{
            animation: `${direction === "left" ? "cal-slide-from-left" : "cal-slide-from-right"} 300ms var(--ease-out) both`,
          }}
        >
          {weeks.map((week, weekIdx) => {
            const bars = weekBars[weekIdx] ?? [];
            const visibleBars = bars.filter((b) => b.rowIndex < 3);
            const overflowBars = bars.filter((b) => b.rowIndex >= 3);
            return (
              <div
                key={weekIdx}
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr)",
                  gridAutoRows: "max-content",
                  gap: 2,
                  minHeight: 100,
                  marginBottom: 2,
                }}
              >
                {week.map(({ date, inMonth }) => {
                  const isToday = date === TODAY;
                  const isFuture = date > TODAY;
                  const entry = entryMap.get(date);
                  const emotion = entry?.emotion;
                  const holiday = holidayMap.get(date);
                  const clickable = inMonth && !isFuture;
                  const handleClick = () => {
                    if (inMonth) {
                      if (clickable) onCellClick(date);
                    } else {
                      const [cellYear, cellMonth] = date.split("-").map(Number);
                      if (
                        cellYear < year ||
                        (cellYear === year && cellMonth < month)
                      )
                        onPrev();
                      else onNext();
                    }
                  };
                  const isHoliday = holiday?.is_holiday === true;
                  const dateNumColor = isToday
                    ? "var(--sage-forest)"
                    : isHoliday
                      ? "var(--accent-clay)"
                      : isFuture && inMonth
                        ? "var(--ink-hint)"
                        : "var(--ink-body)";

                  const borderStyle = (() => {
                    if (isToday) return "2px solid var(--sage-forest)";
                    if (!entry) return "1px solid transparent";
                    if (entry.written_date === undefined)
                      return "2px solid var(--sage-leaf)";
                    if (entry.written_date === date)
                      return "2px solid var(--sage-leaf)";
                    return "2px dashed var(--sage-leaf)";
                  })();

                  return (
                    <button
                      key={date}
                      aria-label={date}
                      disabled={inMonth && isFuture}
                      onClick={handleClick}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: 2,
                        padding: "6px 2px",
                        minHeight: 80,
                        gridRow: 1,
                        borderRadius: "var(--r-2)",
                        border: borderStyle,
                        background: inMonth
                          ? "var(--cal-day-bg, var(--paper-pure))"
                          : "transparent",
                        cursor: clickable || !inMonth ? "pointer" : "default",
                        opacity: inMonth ? 1 : 0.35,
                        transition: "background var(--dur-1)",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-sans)",
                          fontSize: "var(--t-xs)",
                          color: dateNumColor,
                          fontWeight: isToday ? 700 : 400,
                        }}
                      >
                        {new Date(date).getDate()}
                      </span>
                      {holiday && inMonth && (
                        <span
                          style={{
                            fontFamily: "var(--font-sans)",
                            fontSize: 9,
                            lineHeight: 1.2,
                            color: isHoliday
                              ? "var(--accent-clay)"
                              : "var(--ink-hint)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            maxWidth: "100%",
                            display: "block",
                          }}
                        >
                          {truncateName(holiday.name, 4)}
                        </span>
                      )}
                      {emotion ? (
                        <MoodEmoji mood={emotion as Mood} size={18} float />
                      ) : (
                        <span style={{ width: 18, height: 18 }} />
                      )}
                    </button>
                  );
                })}
                {/* 일정 바 — 최대 3개만 표시 */}
                {visibleBars.map((bar, barIdx) => (
                  <button
                    key={`${bar.schedule.id}-w${weekIdx}-${barIdx}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onScheduleClick?.(bar.schedule);
                    }}
                    title={bar.schedule.situation}
                    style={{
                      gridColumn: `${bar.colStart} / ${bar.colEnd}`,
                      gridRow: bar.rowIndex + 2,
                      height: 20,
                      background: "var(--sage-wash)",
                      borderRadius: "var(--r-2, 8px)",
                      border: "none",
                      padding: "0 6px",
                      cursor: onScheduleClick ? "pointer" : "default",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      fontFamily: "var(--font-sans)",
                      fontWeight: 500,
                      fontSize: 11,
                      lineHeight: "20px",
                      color: "var(--sage-ink)",
                      transition: "background var(--dur-2)",
                      animation: "days-fade-in 200ms var(--ease-out) both",
                      pointerEvents: onScheduleClick ? "auto" : "none",
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
                    {bar.schedule.start_time
                      ? `${bar.schedule.start_time.slice(0, 5)} ${bar.schedule.situation}`
                      : bar.schedule.situation}
                  </button>
                ))}
                {/* overflow 일정: "+N개 더" 버튼 (T3.4에서 onClick 연결) */}
                {overflowBars.length > 0 && (
                  <button
                    data-overflow-week={weekIdx}
                    onClick={() => setOpenWeekIdx(weekIdx)}
                    style={{
                      gridColumn: "1 / 8",
                      gridRow: 5,
                      height: 20,
                      background: "transparent",
                      border: "none",
                      padding: "0 6px",
                      cursor: "pointer",
                      fontFamily: "var(--font-sans)",
                      fontWeight: 500,
                      fontSize: 11,
                      lineHeight: "20px",
                      color: "var(--sage-forest)",
                      textAlign: "left",
                      animation: "days-fade-in 200ms var(--ease-out) both",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.color =
                        "var(--sage-ink)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.color =
                        "var(--sage-forest)";
                    }}
                  >
                    +{overflowBars.length}개 더
                  </button>
                )}
                {/* Plan bar — 일자별 점선 구분 세그먼트 */}
                {(planWeekRows[weekIdx] ?? []).flatMap((row) =>
                  row.segments.map((seg) => (
                    <button
                      key={`plan-${seg.plan.id}-${seg.date}`}
                      data-testid={`plan-bar-${seg.plan.id}-${seg.date}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onPlanDayClick?.(seg.plan.id, seg.date);
                      }}
                      title={seg.plan.title}
                      style={{
                        gridColumn: `${seg.colIndex} / ${seg.colIndex + 1}`,
                        gridRow: 6 + row.planRowIndex,
                        height: 18,
                        background: "var(--sage-leaf)",
                        opacity: 0.85,
                        border: "none",
                        borderRight: "1px dashed var(--paper-pure)",
                        padding: 0,
                        paddingLeft: seg.isFirstInWeek ? 4 : 0,
                        cursor: onPlanDayClick ? "pointer" : "default",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontFamily: "var(--font-sans)",
                        fontWeight: 500,
                        fontSize: 10,
                        lineHeight: "18px",
                        color: "var(--paper-pure)",
                        textAlign: "left",
                        animation: "days-fade-in 200ms var(--ease-out) both",
                        pointerEvents: onPlanDayClick ? "auto" : "none",
                      }}
                    >
                      {seg.isFirstInWeek ? truncateName(seg.plan.title, 6) : ""}
                    </button>
                  )),
                )}
              </div>
            );
          })}
        </div>
      </div>
      {/* 주별 일정 더보기 모달 */}
      {openWeekIdx !== null &&
        (() => {
          const allBars = weekBars[openWeekIdx] ?? [];
          const uniqueSchedules = [
            ...new Map(
              allBars.map((b) => [b.schedule.id, b.schedule]),
            ).values(),
          ];
          const weekStart = weeks[openWeekIdx]?.[0]?.date ?? "";
          const weekEnd = weeks[openWeekIdx]?.[6]?.date ?? "";
          const label = weekStart && weekEnd ? `${weekStart} ~ ${weekEnd}` : "";
          return (
            <WeekSchedulesModal
              open
              onClose={() => setOpenWeekIdx(null)}
              schedules={uniqueSchedules}
              weekLabel={label}
              onScheduleClick={(s) => {
                setOpenWeekIdx(null);
                onScheduleClick?.(s);
              }}
            />
          );
        })()}
    </div>
  );
}
