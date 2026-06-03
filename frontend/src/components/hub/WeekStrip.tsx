import { useNavigate } from 'react-router-dom';
import { type WeekDay } from '../../lib/week';
import { MoodEmoji, type Mood } from '../days/MoodEmoji';

interface WeekStripProps {
  days: WeekDay[];
  today: string;
}

const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'];

export function WeekStrip({ days, today }: WeekStripProps) {
  const navigate = useNavigate();

  return (
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
              <MoodEmoji mood={day.emotion as Mood} size={36} float />
            ) : (
              <span style={{ width: 36, height: 27, display: 'inline-block' }} />
            )}
          </button>
        );
      })}
    </div>
  );
}
