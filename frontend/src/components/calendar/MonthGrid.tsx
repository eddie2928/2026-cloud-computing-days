import {
  type CalendarEntry,
  type HolidayItem,
  type ScheduleItem,
} from "../../lib/week";
import { MoodEmoji, type Mood } from "../days/MoodEmoji";
import { Icon } from "../days/Icon";

interface MonthGridProps {
  year: number;
  month: number;
  entries: CalendarEntry[];
  schedules?: ScheduleItem[];
  holidays?: HolidayItem[];
  onPrev: () => void;
  onNext: () => void;
  onCellClick: (date: string) => void;
  onScheduleClick?: (schedule: ScheduleItem) => void;
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

export function MonthGrid({
  year,
  month,
  entries,
  schedules = [],
  holidays = [],
  onPrev,
  onNext,
  onCellClick,
  onScheduleClick,
}: MonthGridProps) {
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

  const weekBars = getScheduleBars(cells, schedules);
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
      <div data-testid="month-grid">
        {weeks.map((week, weekIdx) => {
          const bars = weekBars[weekIdx] ?? [];
          return (
            <div
              key={weekIdx}
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                gridAutoRows: "max-content",
                gap: 2,
                minHeight: 84,
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
                const isHoliday = holiday?.is_holiday === true;
                const dateNumColor = isFuture
                  ? "var(--ink-soft)"
                  : isToday
                    ? "var(--sage-forest)"
                    : isHoliday
                      ? "var(--accent-clay)"
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
                    disabled={isFuture}
                    onClick={() => clickable && onCellClick(date)}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: 2,
                      padding: "6px 2px",
                      minHeight: 60,
                      gridRow: 1,
                      borderRadius: "var(--r-2)",
                      border: borderStyle,
                      background: isFuture
                        ? "var(--paper-mist)"
                        : inMonth
                          ? "var(--cal-day-bg, var(--paper-pure))"
                          : "transparent",
                      cursor: clickable ? "pointer" : "default",
                      opacity: isFuture ? 0.6 : inMonth ? 1 : 0.35,
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
                      <MoodEmoji mood={emotion as Mood} size={12} />
                    ) : (
                      <span style={{ width: 12, height: 12 }} />
                    )}
                  </button>
                );
              })}
              {/* 일정 바 (grid items) */}
              {bars.map((bar, barIdx) => (
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
                    (e.currentTarget as HTMLElement).style.background = "var(--sage-mist)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.background = "var(--sage-wash)";
                  }}
                >
                  {bar.schedule.situation}
                </button>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
