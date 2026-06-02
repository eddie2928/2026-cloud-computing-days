import { useNavigate } from 'react-router-dom';
import { type WeekDay, type ScheduleItem } from '../../lib/week';
import { MoodEmoji, type Mood } from '../days/MoodEmoji';

interface WeekStripProps {
  days: WeekDay[];
  today: string;
  schedules?: ScheduleItem[];
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

export function WeekStrip({ days, today, schedules = [] }: WeekStripProps) {
  const navigate = useNavigate();

  // 이번 주 7일 안에 걸치는 일정만 필터
  const weekStart = days[0]?.date ?? today;
  const weekEnd = days[days.length - 1]?.date ?? today;
  const visibleSchedules = schedules.filter(
    s => s.period_start <= weekEnd && s.period_end >= weekStart
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
    <div style={{ display: 'flex', gap: 4, justifyContent: 'space-between' }}>
      {days.map(day => {
        const isToday = day.date === today;
        const d = new Date(day.date);
        const dayLabel = DAY_LABELS[d.getDay()];
        const dayNum = d.getDate();

        return (
          <button
            key={day.date}
            aria-current={isToday ? 'date' : undefined}
            onClick={() => navigate('/calendar')}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              padding: '10px 4px',
              borderRadius: 'var(--r-3)',
              border: 'none',
              background: isToday ? 'var(--sage-wash)' : 'transparent',
              cursor: 'pointer',
              transition: 'background var(--dur-1)',
            }}
          >
            <span style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-xs)',
              color: isToday ? 'var(--sage-forest)' : 'var(--ink-hint)',
              fontWeight: isToday ? 600 : 400,
            }}>{dayLabel}</span>
            <span style={{
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-sm)',
              color: isToday ? 'var(--sage-ink)' : 'var(--ink-body)',
              fontWeight: isToday ? 700 : 500,
            }}>{dayNum}</span>
            {day.emotion ? (
              <MoodEmoji mood={day.emotion as Mood} size={24} float />
            ) : (
              <span style={{ width: 16, height: 16, display: 'inline-block' }} />
            )}
          </button>
        );
      })}
    </div>

    {/* 일정 바 */}
    {visibleSchedules.length > 0 && (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 2px' }}>
        {visibleSchedules.map(s => (
          <div
            key={s.id}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}
          >
            {days.map((day, i) => {
              const inRange = day.date >= s.period_start && day.date <= s.period_end;
              const isFirst = inRange && (i === 0 || days[i - 1].date < s.period_start);
              const isLast  = inRange && (i === 6 || days[i + 1].date > s.period_end);
              return (
                <div
                  key={day.date}
                  style={{
                    height: 18,
                    background: inRange ? 'var(--paper-pure)' : 'transparent',
                    border: inRange ? '1px solid var(--line)' : 'none',
                    borderRadius: isFirst && isLast ? 99
                      : isFirst ? '99px 0 0 99px'
                      : isLast  ? '0 99px 99px 0'
                      : 0,
                    display: 'flex',
                    alignItems: 'center',
                    paddingLeft: isFirst ? 6 : 0,
                    overflow: 'hidden',
                  }}
                >
                  {isFirst && (
                    <span style={{
                      font: '500 10px/1 var(--font-sans)',
                      color: 'var(--ink-meta)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {s.situation}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    )}
    </div>
  );
}
