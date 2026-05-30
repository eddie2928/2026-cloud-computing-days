import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listPlans } from "../api/plans";
import type { PlanOut } from "../lib/plans";
import { planProgressPercent } from "../lib/plans";
import { ProgressBar } from "../components/plans/ProgressBar";

function formatPeriod(start: string, end: string): string {
  return `${start} ~ ${end}`;
}

interface PlanSummaryCardProps {
  plan: PlanOut;
  onClick: () => void;
}

function PlanSummaryCard({ plan, onClick }: PlanSummaryCardProps) {
  const percent = planProgressPercent(plan);
  return (
    <button
      type="button"
      data-testid="plan-card"
      onClick={onClick}
      style={{
        width: "100%",
        textAlign: "left",
        background: "var(--paper-pure)",
        borderRadius: 18,
        border: "1px solid var(--line)",
        boxShadow: "var(--shadow-card)",
        padding: "20px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        cursor: "pointer",
        animation: "days-rise 320ms var(--ease-out) both",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontWeight: 700,
          fontSize: "var(--t-md)",
          color: "var(--ink-deep)",
          lineHeight: 1.3,
        }}
      >
        {plan.title}
      </div>
      <div
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-xs)",
          color: "var(--ink-soft)",
        }}
      >
        {formatPeriod(plan.period_start, plan.period_end)}
      </div>
      <ProgressBar value={percent} />
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--t-xs)",
          color: "var(--ink-hint)",
          alignSelf: "flex-end",
        }}
      >
        {percent}%
      </div>
    </button>
  );
}

export function Plans() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<PlanOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listPlans()
      .then(setPlans)
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        style={{
          padding: "16px 16px 8px",
          color: "var(--ink-hint)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-sm)",
        }}
      >
        불러오는 중...
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        padding: "16px 16px 8px",
        paddingBottom: 96,
      }}
    >
      <h1
        style={{
          margin: 0,
          fontFamily: "var(--font-sans)",
          fontWeight: 700,
          fontSize: "var(--t-2xl)",
          color: "var(--sage-ink)",
          letterSpacing: "-0.015em",
          animation: "days-rise 320ms var(--ease-out) both",
        }}
      >
        오늘의 계획
      </h1>

      {plans.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16,
            padding: "48px 0",
            animation: "days-pop 380ms var(--ease-soft) both",
          }}
        >
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-base)",
              color: "var(--ink-hint)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            아직 만든 Plan이 없어요.
            <br />
            새 Plan을 만들어보세요.
          </p>
          <button
            type="button"
            onClick={() => navigate("/plans/new")}
            style={{
              padding: "12px 28px",
              background: "var(--sage-leaf)",
              color: "var(--paper-pure)",
              border: "none",
              borderRadius: "var(--r-pill)",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: "var(--t-sm)",
              cursor: "pointer",
              boxShadow: "var(--shadow-2)",
            }}
          >
            새 Plan 만들기
          </button>
        </div>
      ) : (
        plans.map((plan, i) => (
          <div
            key={plan.id}
            style={{ animation: `days-rise 320ms var(--ease-out) ${80 + i * 60}ms both` }}
          >
            <PlanSummaryCard
              plan={plan}
              onClick={() => navigate(`/plans/${plan.id}`)}
            />
          </div>
        ))
      )}

      {/* Fixed "Plan 추가" button above bottom nav */}
      <div
        style={{
          position: "fixed",
          bottom: 72,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 50,
        }}
      >
        <button
          type="button"
          onClick={() => navigate("/plans/new")}
          style={{
            padding: "13px 32px",
            background: "var(--sage-leaf)",
            color: "var(--paper-pure)",
            border: "none",
            borderRadius: "var(--r-pill)",
            fontFamily: "var(--font-sans)",
            fontWeight: 600,
            fontSize: "var(--t-sm)",
            cursor: "pointer",
            boxShadow: "var(--shadow-3)",
            whiteSpace: "nowrap",
          }}
        >
          + Plan 추가
        </button>
      </div>
    </div>
  );
}
