interface DailyTodoCardProps {
  onClick: () => void;
  planCount: number;
  activeTodayTodos: number;
}

export function DailyTodoCard({ onClick, planCount, activeTodayTodos }: DailyTodoCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: '100%',
        textAlign: 'left',
        background: 'var(--paper-pure)',
        borderRadius: 'var(--r-card, 18px)',
        border: '1px solid var(--line)',
        boxShadow: 'var(--shadow-card)',
        padding: '20px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        cursor: 'pointer',
        animation: 'days-rise 320ms var(--ease-out) 160ms both',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontWeight: 500,
          fontSize: 12,
          color: 'var(--ink-hint)',
          letterSpacing: '0.04em',
        }}
      >
        오늘의 계획
      </div>

      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontWeight: 700,
          fontSize: 'var(--t-lg, 20px)',
          color: 'var(--ink-body)',
          lineHeight: 1.2,
        }}
      >
        {activeTodayTodos > 0 ? (
          <>
            <span style={{ color: 'var(--sage-leaf)', marginRight: 4 }}>{activeTodayTodos}</span>
            할 일
          </>
        ) : (
          <span style={{ color: 'var(--ink-hint)', fontWeight: 500, fontSize: 'var(--t-base)' }}>
            오늘은 비어 있어요
          </span>
        )}
      </div>

      <div
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 'var(--t-sm, 13px)',
          color: 'var(--ink-soft)',
        }}
      >
        진행 중인 Plan {planCount}개
      </div>
    </button>
  );
}
