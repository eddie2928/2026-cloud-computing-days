import { type CalendarEntry } from '../../lib/week';
import { MoodEmoji, type Mood } from '../days/MoodEmoji';
import { Icon } from '../days/Icon';

interface MonthGridProps {
  year: number;
  month: number;
  entries: CalendarEntry[];
  onPrev: () => void;
  onNext: () => void;
  onCellClick: (date: string) => void;
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];
const TODAY = new Date().toISOString().split('T')[0];

export function MonthGrid({ year, month, entries, onPrev, onNext, onCellClick }: MonthGridProps) {
  const entryMap = new Map(entries.map(e => [e.date, e.emotion]));
  const firstDay = new Date(year, month - 1, 1);
  const startOffset = firstDay.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const daysInPrev = new Date(year, month - 1, 0).getDate();

  const cells: Array<{ date: string; inMonth: boolean }> = [];

  for (let i = startOffset - 1; i >= 0; i--) {
    const prevMonth = month === 1 ? 12 : month - 1;
    const prevYear = month === 1 ? year - 1 : year;
    const d = daysInPrev - i;
    cells.push({ date: `${prevYear}-${String(prevMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`, inMonth: false });
  }

  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ date: `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`, inMonth: true });
  }

  const remaining = 42 - cells.length;
  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  for (let d = 1; d <= remaining; d++) {
    cells.push({ date: `${nextYear}-${String(nextMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`, inMonth: false });
  }

  return (
    <div>
      {/* 월 네비게이션 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 4px 16px' }}>
        <button
          aria-label="이전 달"
          onClick={onPrev}
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--ink-body)', padding: 8 }}
        >
          <Icon name="chevron-left" size={20} />
        </button>
        <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 'var(--t-md)', color: 'var(--sage-ink)', letterSpacing: '-0.01em' }}>
          {year}.{String(month).padStart(2, '0')}
        </span>
        <button
          aria-label="다음 달"
          onClick={onNext}
          style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--ink-body)', padding: 8 }}
        >
          <Icon name="chevron-right" size={20} />
        </button>
      </div>

      {/* 요일 헤더 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', marginBottom: 4 }}>
        {DAY_LABELS.map(d => (
          <div key={d} style={{ textAlign: 'center', fontFamily: 'var(--font-sans)', fontSize: 'var(--t-xs)', color: 'var(--cal-weekday-label, var(--ink-hint))', padding: '4px 0' }}>
            {d}
          </div>
        ))}
      </div>

      {/* 날짜 셀 그리드 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }} data-testid="month-grid">
        {cells.map(({ date, inMonth }) => {
          const isToday = date === TODAY;
          const emotion = entryMap.get(date);
          return (
            <button
              key={date}
              aria-label={date}
              onClick={() => inMonth && onCellClick(date)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 2,
                padding: '6px 2px',
                borderRadius: 'var(--r-2)',
                border: isToday ? '1.5px solid var(--sage-leaf)' : '1px solid transparent',
                background: inMonth ? 'var(--cal-day-bg, var(--paper-pure))' : 'transparent',
                cursor: inMonth ? 'pointer' : 'default',
                opacity: inMonth ? 1 : 0.35,
                transition: 'background var(--dur-1)',
              }}
            >
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: 'var(--t-xs)', color: isToday ? 'var(--sage-leaf)' : 'var(--ink-body)', fontWeight: isToday ? 700 : 400 }}>
                {new Date(date).getDate()}
              </span>
              {emotion ? <MoodEmoji mood={emotion as Mood} size={12} /> : <span style={{ width: 12, height: 12 }} />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
