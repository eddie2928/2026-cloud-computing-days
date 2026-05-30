import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getPlan, deletePlan } from "../api/plans";
import type { PlanWithTodosOut } from "../lib/plans";
import { planProgressPercent } from "../lib/plans";
import { ProgressBar } from "../components/plans/ProgressBar";
import PlanMiniCalendar from "../components/plans/PlanMiniCalendar";
import { useMockDate } from "../hooks/useMockDate";

interface DeleteModalProps {
  title: string;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteModal({ title, onConfirm, onCancel }: DeleteModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Plan 삭제 확인"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(31, 40, 24, 0.40)",
      }}
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--paper-pure)",
          borderRadius: 20,
          padding: "28px 24px",
          width: "calc(100% - 48px)",
          maxWidth: 360,
          boxShadow: "var(--shadow-3)",
          display: "flex",
          flexDirection: "column",
          gap: 20,
          animation: "days-pop 260ms var(--ease-soft) both",
        }}
      >
        <div>
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: "var(--t-md)",
              color: "var(--ink-deep)",
            }}
          >
            Plan을 삭제할까요?
          </p>
          <p
            style={{
              margin: "8px 0 0",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-hint)",
            }}
          >
            "{title}" 과 관련된 모든 할 일이 삭제됩니다.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              flex: 1,
              padding: "12px 0",
              background: "var(--sage-cloud)",
              border: "none",
              borderRadius: "var(--r-pill)",
              fontFamily: "var(--font-sans)",
              fontWeight: 500,
              fontSize: "var(--t-sm)",
              color: "var(--ink-body)",
              cursor: "pointer",
            }}
          >
            취소
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              flex: 1,
              padding: "12px 0",
              background: "var(--accent-clay)",
              border: "none",
              borderRadius: "var(--r-pill)",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: "var(--t-sm)",
              color: "var(--paper-pure)",
              cursor: "pointer",
            }}
          >
            삭제
          </button>
        </div>
      </div>
    </div>
  );
}

export function PlanDetail() {
  const navigate = useNavigate();
  const { planId } = useParams<{ planId: string }>();
  const id = Number(planId);
  const today = useMockDate();

  const [plan, setPlan] = useState<PlanWithTodosOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    getPlan(id)
      .then((data) => {
        setPlan(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Plan을 불러오지 못했어요.");
        setLoading(false);
      });
  }, [id]);

  const handleDelete = async () => {
    if (!plan) return;
    setDeleting(true);
    try {
      await deletePlan(plan.id);
      navigate("/plans");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          padding: "16px",
          color: "var(--ink-hint)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-sm)",
        }}
      >
        불러오는 중...
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div
        style={{
          padding: "16px",
          color: "var(--accent-clay)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-sm)",
        }}
      >
        {error ?? "Plan을 찾을 수 없어요."}
      </div>
    );
  }

  const overallPercent = planProgressPercent(plan);

  return (
    <>
      {confirmDelete && (
        <DeleteModal
          title={plan.title}
          onConfirm={handleDelete}
          onCancel={() => setConfirmDelete(false)}
        />
      )}

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 0,
          paddingBottom: 96,
        }}
      >
        {/* Header */}
        <div
          style={{
            position: "sticky",
            top: 0,
            zIndex: 10,
            background: "var(--paper-bone)",
            padding: "12px 16px 10px",
            borderBottom: "1px solid var(--line-faint)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <button
            type="button"
            aria-label="뒤로 가기"
            onClick={() => navigate(-1)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-lg)",
              color: "var(--ink-body)",
              padding: "4px 8px 4px 0",
              lineHeight: 1,
            }}
          >
            ←
          </button>

          <span
            style={{
              flex: 1,
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: "var(--t-sm)",
              color: "var(--ink-meta)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            Plan
          </span>

          <button
            type="button"
            aria-label="Plan 편집"
            onClick={() => navigate(`/plans/${id}/edit`)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 18,
              color: "var(--ink-meta)",
              padding: "4px",
              lineHeight: 1,
            }}
          >
            ✏️
          </button>
          <button
            type="button"
            aria-label="Plan 삭제"
            onClick={() => setConfirmDelete(true)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 18,
              color: "var(--accent-clay)",
              padding: "4px",
              lineHeight: 1,
            }}
          >
            🗑️
          </button>
        </div>

        {/* Plan meta */}
        <div
          style={{
            padding: "20px 16px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            animation: "days-rise 320ms var(--ease-out) both",
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
              lineHeight: 1.25,
            }}
          >
            {plan.title}
          </h1>
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-soft)",
            }}
          >
            {plan.period_start} ~ {plan.period_end}
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "var(--t-xs)",
                color: "var(--ink-hint)",
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>전체 진척도</span>
              <span style={{ fontFamily: "var(--font-mono)", color: "var(--sage-leaf)" }}>
                {overallPercent}%
              </span>
            </div>
            <ProgressBar value={overallPercent} />
          </div>
        </div>

        {/* Mini calendar */}
        <div style={{ padding: "0 16px 24px" }}>
          <PlanMiniCalendar
            plan={plan}
            todayStr={today}
            onSelectDate={(d) => navigate(`/plans/${id}/day/${d}`)}
          />
        </div>
      </div>

      {deleting && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(31, 40, 24, 0.25)",
            fontFamily: "var(--font-sans)",
            color: "var(--ink-hint)",
            fontSize: "var(--t-sm)",
          }}
        >
          삭제 중...
        </div>
      )}
    </>
  );
}
