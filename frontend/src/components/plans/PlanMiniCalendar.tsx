import { useState } from 'react';
import type { PlanWithTodosOut } from '../../lib/plans';
import { todosByDate } from '../../lib/plans';

interface Props {
  plan: PlanWithTodosOut;
  todayStr: string;
  onSelectDate: (date: string) => void;
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

function toYM(dateStr: string): { year: number; month: number } {
  const [y, m] = dateStr.split('-').map(Number);
  return { year: y, month: m };
}

function ymKey(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`;
}

function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const d = new Date(year, month - 1 + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

function buildGridDates(year: number, month: number): string[] {
  const firstDay = new Date(year, month - 1, 1);
  const lastDay = new Date(year, month, 0);
  const startOffset = firstDay.getDay(); // 0=Sunday
  const dates: string[] = [];

  // Fill leading days from previous month
  for (let i = startOffset - 1; i >= 0; i--) {
    const d = new Date(year, month - 1, -i);
    dates.push(d.toISOString().slice(0, 10));
  }

  // Current month days
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const dd = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    dates.push(dd);
  }

  // Fill trailing days to reach 42
  let next = 1;
  while (dates.length < 42) {
    const d = new Date(year, month, next++);
    dates.push(d.toISOString().slice(0, 10));
  }

  return dates;
}

export default function PlanMiniCalendar({ plan, todayStr, onSelectDate }: Props) {
  const startYM = toYM(plan.period_start);
  const endYM = toYM(plan.period_end);

  const [cur, setCur] = useState({ year: startYM.year, month: startYM.month });

  const byDate = todosByDate(plan.todos);

  const prevDisabled = ymKey(cur.year, cur.month) <= ymKey(startYM.year, startYM.month);
  const nextDisabled = ymKey(cur.year, cur.month) >= ymKey(endYM.year, endYM.month);

  const gridDates = buildGridDates(cur.year, cur.month);

  const monthLabel = `${cur.year}년 ${cur.month}월`;

  return (
    <div style={{ width: '100%' }}>
      {/* Month navigation */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 12,
      }}>
        <button
          onClick={() => setCur(addMonths(cur.year, cur.month, -1))}
          disabled={prevDisabled}
          aria-label="이전 달"
          style={{
            background: 'none',
            border: '1.5px solid var(--line)',
            borderRadius: 999,
            width: 32,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: prevDisabled ? 'not-allowed' : 'pointer',
            color: prevDisabled ? 'var(--ink-soft)' : 'var(--ink-meta)',
            fontSize: 14,
            transition: 'opacity var(--dur-1) var(--ease-out)',
            opacity: prevDisabled ? 0.4 : 1,
          }}
        >
          ‹
        </button>

        <span style={{
          font: '600 15px/1 var(--font-sans)',
          color: 'var(--ink-deep)',
          letterSpacing: '-0.01em',
        }}>
          {monthLabel}
        </span>

        <button
          onClick={() => setCur(addMonths(cur.year, cur.month, 1))}
          disabled={nextDisabled}
          aria-label="다음 달"
          style={{
            background: 'none',
            border: '1.5px solid var(--line)',
            borderRadius: 999,
            width: 32,
            height: 32,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: nextDisabled ? 'not-allowed' : 'pointer',
            color: nextDisabled ? 'var(--ink-soft)' : 'var(--ink-meta)',
            fontSize: 14,
            transition: 'opacity var(--dur-1) var(--ease-out)',
            opacity: nextDisabled ? 0.4 : 1,
          }}
        >
          ›
        </button>
      </div>

      {/* Day labels */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        marginBottom: 4,
      }}>
        {DAY_LABELS.map((d) => (
          <div key={d} style={{
            textAlign: 'center',
            font: '500 11px/1 var(--font-sans)',
            color: 'var(--ink-hint)',
            paddingBottom: 6,
          }}>
            {d}
          </div>
        ))}
      </div>

      {/* Date grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 2,
      }}>
        {gridDates.map((dateStr) => {
          const inPeriod = dateStr >= plan.period_start && dateStr <= plan.period_end;
          const isFuture = dateStr > todayStr;
          const isToday = dateStr === todayStr;
          const todos = byDate[dateStr] ?? [];
          const total = todos.length;
          const done = todos.filter((t) => t.completed).length;
          const isComplete = total > 0 && done === total;
          const clickable = inPeriod && !isFuture;

          let bg = 'transparent';
          let borderColor = 'transparent';
          let textColor = 'var(--ink-body)';
          let cursor = 'default';

          if (!inPeriod) {
            textColor = 'var(--ink-soft)';
          } else if (isComplete) {
            bg = 'var(--sage-wash)';
            textColor = 'var(--sage-forest)';
          } else if (isFuture) {
            bg = 'var(--sage-cloud)';
            textColor = 'var(--ink-hint)';
          } else {
            cursor = 'pointer';
          }

          if (isToday) {
            borderColor = 'var(--sage-leaf)';
          }

          return (
            <button
              key={dateStr}
              onClick={() => clickable && onSelectDate(dateStr)}
              disabled={!clickable}
              aria-label={dateStr}
              data-testid={`cell-${dateStr}`}
              style={{
                background: bg,
                border: `1.5px solid ${borderColor}`,
                borderRadius: 8,
                padding: '5px 2px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 2,
                cursor: clickable ? cursor : 'default',
                outline: 'none',
                transition: 'background var(--dur-1) var(--ease-out)',
              }}
            >
              <span style={{
                font: `${isToday ? '700' : '400'} 12px/1 var(--font-sans)`,
                color: inPeriod ? (isToday ? 'var(--sage-forest)' : textColor) : 'var(--ink-soft)',
              }}>
                {Number(dateStr.slice(8))}
              </span>
              {inPeriod && (
                <span style={{
                  font: '400 9px/1 var(--font-sans)',
                  color: isComplete ? 'var(--sage-leaf)' : (isFuture ? 'var(--ink-hint)' : 'var(--ink-meta)'),
                }}>
                  {done}/{total}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
