import { PillButton } from '../days/PillButton';

interface TodayDiaryCardProps {
  today: string;
  hasDiary: boolean;
  summary?: string;
  onOpen: (date: string) => void;
  onStart?: () => void;
}

export function TodayDiaryCard({ today, hasDiary, summary, onOpen, onStart }: TodayDiaryCardProps) {
  return (
    <div style={{
      background: 'var(--paper-pure)',
      borderRadius: 'var(--r-5)',
      border: '1px solid var(--line-faint)',
      boxShadow: 'var(--shadow-card)',
      padding: '20px 18px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      flex: 1,
    }}>
      <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 'var(--t-sm)', color: 'var(--ink-meta)', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
        오늘의 일기
      </div>
      {hasDiary && summary ? (
        <>
          <p style={{ margin: 0, fontFamily: 'var(--font-sans)', fontSize: 'var(--t-base)', color: 'var(--ink-body)', lineHeight: 1.6, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
            {summary}
          </p>
          <PillButton onClick={() => onOpen(today)} style={{ marginTop: 4 }}>
            이어보기
          </PillButton>
        </>
      ) : (
        <>
          <p style={{ margin: 0, fontFamily: 'var(--font-sans)', fontSize: 'var(--t-base)', color: 'var(--ink-hint)' }}>
            아직 오늘의 일기가 없어요
          </p>
          <PillButton onClick={() => onStart ? onStart() : onOpen(today)}>
            오늘의 일기 시작
          </PillButton>
        </>
      )}
    </div>
  );
}
