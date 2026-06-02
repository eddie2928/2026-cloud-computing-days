import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getPlan, updatePlan, bulkReplaceTodos } from "../api/plans";
import type { PlanWithTodosOut } from "../lib/plans";

interface TodoRow {
  id: string;
  content: string;
}

let rowCounter = 0;
function newRow(content = ""): TodoRow {
  return { id: `r${++rowCounter}`, content };
}

export function PlanEdit() {
  const navigate = useNavigate();
  const { planId } = useParams<{ planId: string }>();
  const id = Number(planId);

  const [plan, setPlan] = useState<PlanWithTodosOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [rows, setRows] = useState<TodoRow[]>([newRow()]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getPlan(id)
      .then((data) => {
        setPlan(data);
        setTitle(data.title);
        setPeriodStart(data.period_start);
        setPeriodEnd(data.period_end);

        // Seed rows from period_start day's todos, or earliest day, or empty
        const todosOnStart = data.todos
          .filter((t) => t.todo_date === data.period_start)
          .sort((a, b) => a.sequence - b.sequence);

        if (todosOnStart.length > 0) {
          setRows(todosOnStart.map((t) => newRow(t.content)));
        } else {
          const allDates = [...new Set(data.todos.map((t) => t.todo_date))].sort();
          if (allDates.length > 0) {
            const earliest = allDates[0];
            const earlyTodos = data.todos
              .filter((t) => t.todo_date === earliest)
              .sort((a, b) => a.sequence - b.sequence);
            setRows(earlyTodos.map((t) => newRow(t.content)));
          } else {
            setRows([newRow()]);
          }
        }

        setLoading(false);
      })
      .catch(() => {
        setFetchError("Plan을 불러오지 못했어요.");
        setLoading(false);
      });
  }, [id]);

  const addRow = () => setRows((prev) => [...prev, newRow()]);

  const removeRow = (rowId: string) =>
    setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.id !== rowId) : prev));

  const moveRow = (rowId: string, dir: -1 | 1) => {
    setRows((prev) => {
      const idx = prev.findIndex((r) => r.id === rowId);
      const next = idx + dir;
      if (next < 0 || next >= prev.length) return prev;
      const copy = [...prev];
      [copy[idx], copy[next]] = [copy[next], copy[idx]];
      return copy;
    });
  };

  const updateRowContent = (rowId: string, content: string) =>
    setRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, content } : r)));

  const handleSave = async () => {
    if (!plan) return;
    setSaving(true);
    setSaveError(null);
    try {
      const metaChanged =
        title.trim() !== plan.title ||
        periodStart !== plan.period_start ||
        periodEnd !== plan.period_end;

      if (metaChanged) {
        await updatePlan(plan.id, {
          title: title.trim() || plan.title,
          period_start: periodStart,
          period_end: periodEnd,
        });
      }

      const contents = rows.map((r) => r.content.trim()).filter((c) => c.length > 0);
      await bulkReplaceTodos(plan.id, contents);

      navigate(`/plans/${id}`);
    } catch {
      setSaveError("저장에 실패했어요. 다시 시도해주세요.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 16, color: "var(--ink-hint)", fontFamily: "var(--font-sans)", fontSize: "var(--t-sm)" }}>
        불러오는 중...
      </div>
    );
  }

  if (fetchError || !plan) {
    return (
      <div style={{ padding: 16, color: "var(--accent-clay)", fontFamily: "var(--font-sans)", fontSize: "var(--t-sm)" }}>
        {fetchError ?? "Plan을 찾을 수 없어요."}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--paper-bone)" }}>
      {/* Header */}
      <div style={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: "var(--paper-bone)",
        padding: "12px 16px 10px",
        borderBottom: "1px solid var(--line-faint)",
        display: "flex",
        alignItems: "center",
        gap: 10,
      }}>
        <button
          type="button"
          aria-label="취소"
          onClick={() => navigate(`/plans/${id}`)}
          style={{
            background: "none", border: "none", cursor: "pointer",
            fontFamily: "var(--font-sans)", fontSize: "var(--t-lg)",
            color: "var(--ink-body)", padding: "4px 8px 4px 0", lineHeight: 1,
          }}
        >
          ←
        </button>
        <span style={{
          flex: 1,
          fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: "var(--t-sm)",
          color: "var(--ink-meta)",
        }}>
          Plan 수정
        </span>
      </div>

      {/* Content */}
      <div style={{ flex: 1, padding: "20px 16px 24px", display: "flex", flexDirection: "column", gap: 24 }}>

        {/* Title */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ font: "500 13px/1 var(--font-sans)", color: "var(--ink-meta)" }}>
            Plan 이름
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Plan 이름"
            style={{
              padding: "12px 16px",
              borderRadius: 999,
              border: "1.5px solid var(--line)",
              background: "var(--paper-bone)",
              font: "400 15px/1.4 var(--font-sans)",
              color: "var(--ink-deep)",
              outline: "none",
            }}
          />
        </div>

        {/* Period */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ font: "500 13px/1 var(--font-sans)", color: "var(--ink-meta)" }}>
            기간
          </label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              style={{
                flex: 1, padding: "10px 14px",
                border: "1.5px solid var(--line)", borderRadius: 12,
                background: "var(--paper-bone)",
                font: "400 14px/1 var(--font-sans)", color: "var(--ink-deep)",
                outline: "none",
              }}
            />
            <span style={{ color: "var(--ink-soft)", font: "400 14px/1 var(--font-sans)" }}>~</span>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              style={{
                flex: 1, padding: "10px 14px",
                border: "1.5px solid var(--line)", borderRadius: 12,
                background: "var(--paper-bone)",
                font: "400 14px/1 var(--font-sans)", color: "var(--ink-deep)",
                outline: "none",
              }}
            />
          </div>
        </div>

        {/* Todo template */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <label style={{ font: "500 13px/1 var(--font-sans)", color: "var(--ink-meta)" }}>
            매일 할 일 템플릿
          </label>
          <p style={{ margin: 0, font: "400 12px/1.5 var(--font-sans)", color: "var(--ink-hint)" }}>
            오늘 이후 날짜에 일괄 적용됩니다. 과거 날짜는 유지됩니다.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {rows.map((row, idx) => (
              <div key={row.id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {/* Move up/down */}
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <button
                    type="button"
                    aria-label="위로 이동"
                    onClick={() => moveRow(row.id, -1)}
                    disabled={idx === 0}
                    style={{
                      background: "none", border: "none",
                      cursor: idx === 0 ? "default" : "pointer",
                      color: idx === 0 ? "var(--ink-soft)" : "var(--ink-meta)",
                      font: "400 10px/1 var(--font-sans)", padding: "2px 4px",
                    }}
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    aria-label="아래로 이동"
                    onClick={() => moveRow(row.id, 1)}
                    disabled={idx === rows.length - 1}
                    style={{
                      background: "none", border: "none",
                      cursor: idx === rows.length - 1 ? "default" : "pointer",
                      color: idx === rows.length - 1 ? "var(--ink-soft)" : "var(--ink-meta)",
                      font: "400 10px/1 var(--font-sans)", padding: "2px 4px",
                    }}
                  >
                    ▼
                  </button>
                </div>

                <input
                  value={row.content}
                  onChange={(e) => updateRowContent(row.id, e.target.value)}
                  placeholder={`할 일 ${idx + 1}`}
                  data-testid={`todo-row-${idx}`}
                  style={{
                    flex: 1, padding: "10px 14px",
                    border: "1.5px solid var(--line)", borderRadius: 12,
                    background: "var(--paper-pure)",
                    font: "400 14px/1.4 var(--font-sans)", color: "var(--ink-deep)",
                    outline: "none",
                  }}
                />

                <button
                  type="button"
                  aria-label="행 삭제"
                  onClick={() => removeRow(row.id)}
                  disabled={rows.length === 1}
                  style={{
                    background: "none", border: "none",
                    cursor: rows.length === 1 ? "default" : "pointer",
                    color: rows.length === 1 ? "var(--ink-soft)" : "var(--accent-clay)",
                    font: "400 16px/1 var(--font-sans)", padding: "4px",
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={addRow}
            style={{
              alignSelf: "flex-start",
              background: "none",
              border: "1px dashed var(--line)",
              borderRadius: 10,
              padding: "7px 16px",
              font: "400 13px/1 var(--font-sans)",
              color: "var(--ink-hint)",
              cursor: "pointer",
              marginTop: 4,
            }}
          >
            + 항목 추가
          </button>
        </div>

        {saveError && (
          <p style={{ margin: 0, font: "400 13px/1.4 var(--font-sans)", color: "var(--accent-clay)" }}>
            {saveError}
          </p>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            style={{
              flex: 1,
              background: saving ? "var(--sage-mist)" : "var(--sage-leaf)",
              border: "none",
              borderRadius: "var(--r-pill)",
              padding: "10px 0",
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: 14,
              color: "var(--paper-pure)",
              cursor: saving ? "wait" : "pointer",
              opacity: saving ? 0.7 : 1,
              transition: "background var(--dur-1) var(--ease-out)",
            }}
          >
            {saving ? "저장 중..." : "저장"}
          </button>
          <button
            type="button"
            onClick={() => navigate(`/plans/${id}`)}
            style={{
              background: "transparent",
              border: "none",
              borderRadius: "var(--r-3)",
              padding: "10px 16px",
              fontFamily: "var(--font-sans)",
              fontWeight: 500,
              fontSize: 14,
              color: "var(--ink-meta)",
              cursor: "pointer",
            }}
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
