import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { getPlan, updateTodo } from "../api/plans";
import type { PlanWithTodosOut, PlanTodoOut } from "../lib/plans";
import { planProgressPercent } from "../lib/plans";
import { ProgressBar } from "../components/plans/ProgressBar";
import { useMockDate } from "../hooks/useMockDate";

function formatDateKo(dateStr: string): string {
  const [year, month, day] = dateStr.split("-").map(Number);
  const d = new Date(year, month - 1, day);
  const dayNames = ["일", "월", "화", "수", "목", "금", "토"];
  return `${year}년 ${month}월 ${day}일 (${dayNames[d.getDay()]})`;
}

export function PlanDayDetail() {
  const navigate = useNavigate();
  const { planId, date } = useParams<{ planId: string; date: string }>();
  const today = useMockDate();
  const id = Number(planId);
  const isToday = date === today;

  const [plan, setPlan] = useState<PlanWithTodosOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlan = () => {
    if (!id || !date) return;
    setLoading(true);
    getPlan(id)
      .then((data) => {
        setPlan(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Plan을 불러오지 못했어요.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPlan();
  }, [id, date]);

  const handleToggle = async (todo: PlanTodoOut) => {
    if (!plan || !isToday) return;
    await updateTodo(plan.id, todo.id, { completed: !todo.completed });
    fetchPlan();
  };

  if (loading) {
    return (
      <div
        style={{
          padding: 16,
          color: "var(--ink-hint)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-sm)",
        }}
      >
        불러오는 중...
      </div>
    );
  }

  if (error || !plan || !date) {
    return (
      <div
        style={{
          padding: 16,
          color: "var(--accent-clay)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--t-sm)",
        }}
      >
        {error ?? "Plan을 찾을 수 없어요."}
      </div>
    );
  }

  const dayTodos = plan.todos
    .filter((t) => t.todo_date === date)
    .sort((a, b) => a.sequence - b.sequence);
  const overallPercent = planProgressPercent(plan);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        paddingBottom: 96,
        animation: "days-rise 320ms var(--ease-out) both",
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
          }}
        >
          하루 할 일
        </span>
      </div>

      {/* Plan meta card */}
      <div
        style={{
          margin: "16px 16px 0",
          background: "var(--paper-pure)",
          border: "1px solid var(--line)",
          borderRadius: 20,
          padding: "20px 20px 16px",
          boxShadow: "var(--shadow-card)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-sans)",
            fontWeight: 700,
            fontSize: "var(--t-xl)",
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
            fontSize: "var(--t-xs)",
            color: "var(--ink-soft)",
          }}
        >
          {plan.period_start} ~ {plan.period_end}
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-xs)",
              color: "var(--ink-hint)",
            }}
          >
            <span>전체 진척도</span>
            <span style={{ color: "var(--sage-leaf)" }}>{overallPercent}%</span>
          </div>
          <ProgressBar value={overallPercent} />
        </div>
      </div>

      {/* Date heading */}
      <div
        style={{
          padding: "20px 16px 12px",
          fontFamily: "var(--font-sans)",
          fontWeight: 600,
          fontSize: "var(--t-md)",
          color: isToday ? "var(--sage-forest)" : "var(--ink-body)",
          letterSpacing: "-0.01em",
        }}
      >
        {formatDateKo(date)}
        {isToday && (
          <span
            style={{
              marginLeft: 8,
              fontWeight: 400,
              fontSize: "var(--t-xs)",
              color: "var(--sage-leaf)",
            }}
          >
            오늘
          </span>
        )}
      </div>

      {/* Todo list */}
      <div style={{ padding: "0 16px" }}>
        {dayTodos.length === 0 ? (
          <div
            data-testid="empty-state"
            style={{
              padding: "32px 0",
              textAlign: "center",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-hint)",
            }}
          >
            이 날에는 할 일이 없어요.
          </div>
        ) : (
          <ul
            style={{
              margin: 0,
              padding: 0,
              listStyle: "none",
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {dayTodos.map((todo) => (
              <li
                key={todo.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 4px",
                  borderBottom: "1px solid var(--line-faint)",
                }}
              >
                <button
                  type="button"
                  aria-label={todo.completed ? "완료 취소" : "완료 처리"}
                  disabled={!isToday}
                  onClick={() => handleToggle(todo)}
                  style={{
                    flexShrink: 0,
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    border: `2px solid ${
                      !isToday
                        ? "var(--line)"
                        : todo.completed
                          ? "var(--sage-leaf)"
                          : "var(--line-strong)"
                    }`,
                    background: todo.completed && isToday ? "var(--sage-leaf)" : "transparent",
                    cursor: isToday ? "pointer" : "not-allowed",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: 0,
                    opacity: isToday ? 1 : 0.45,
                    transition: "all var(--dur-2) var(--ease-out)",
                  }}
                >
                  {todo.completed && isToday && (
                    <span
                      style={{
                        color: "var(--paper-pure)",
                        fontSize: 12,
                        lineHeight: 1,
                      }}
                    >
                      ✓
                    </span>
                  )}
                </button>
                <span
                  style={{
                    flex: 1,
                    fontFamily: "var(--font-sans)",
                    fontSize: "var(--t-sm)",
                    color:
                      !isToday
                        ? "var(--ink-hint)"
                        : todo.completed
                          ? "var(--ink-hint)"
                          : "var(--ink-body)",
                    textDecoration:
                      todo.completed && isToday ? "line-through" : "none",
                    lineHeight: 1.5,
                  }}
                >
                  {todo.content}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer link */}
      <div
        style={{
          padding: "24px 16px 0",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Link
          to={`/plans/${plan.id}`}
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: "var(--t-sm)",
            color: "var(--sage-forest)",
            textDecoration: "none",
            padding: "10px 20px",
            border: "1.5px solid var(--sage-leaf)",
            borderRadius: 999,
            display: "inline-block",
            transition: "background var(--dur-1) var(--ease-out)",
          }}
        >
          Plan 수정 페이지로
        </Link>
      </div>
    </div>
  );
}
