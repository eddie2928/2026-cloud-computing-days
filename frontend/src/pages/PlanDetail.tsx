import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getPlan, updatePlan, deletePlan, createTodo, updateTodo, deleteTodo } from "../api/plans";
import type { PlanWithTodosOut, PlanTodoOut } from "../lib/plans";
import { planProgressPercent, todosByDate, dateRangeInclusive } from "../lib/plans";
import { ProgressBar } from "../components/plans/ProgressBar";

function formatDateKo(dateStr: string): string {
  const [year, month, day] = dateStr.split("-").map(Number);
  const d = new Date(year, month - 1, day);
  const dayNames = ["일", "월", "화", "수", "목", "금", "토"];
  return `${month}월 ${day}일 (${dayNames[d.getDay()]})`;
}

function dateTodoProgress(todos: PlanTodoOut[], date: string): number {
  const dateTodos = todos.filter((t) => t.todo_date === date);
  if (dateTodos.length === 0) return 0;
  return Math.round((dateTodos.filter((t) => t.completed).length / dateTodos.length) * 100);
}

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

  const [plan, setPlan] = useState<PlanWithTodosOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Plan meta editing
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editStart, setEditStart] = useState("");
  const [editEnd, setEditEnd] = useState("");
  const [saving, setSaving] = useState(false);

  // Delete
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Todo inline editing
  const [editingTodoId, setEditingTodoId] = useState<number | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const todoEditRef = useRef<HTMLInputElement | null>(null);

  // Todo add (per date)
  const [addingDate, setAddingDate] = useState<string | null>(null);
  const [newContent, setNewContent] = useState("");
  const addInputRef = useRef<HTMLInputElement | null>(null);

  const refetch = () => {
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
  };

  useEffect(() => {
    refetch();
  }, [id]);

  useEffect(() => {
    if (addingDate && addInputRef.current) {
      addInputRef.current.focus();
    }
  }, [addingDate]);

  useEffect(() => {
    if (editingTodoId !== null && todoEditRef.current) {
      todoEditRef.current.focus();
    }
  }, [editingTodoId]);

  const startEdit = () => {
    if (!plan) return;
    setEditTitle(plan.title);
    setEditStart(plan.period_start);
    setEditEnd(plan.period_end);
    setEditing(true);
  };

  const submitEdit = async () => {
    if (!plan) return;
    setSaving(true);
    try {
      await updatePlan(plan.id, {
        title: editTitle.trim() || plan.title,
        period_start: editStart,
        period_end: editEnd,
      });
      setEditing(false);
      refetch();
    } finally {
      setSaving(false);
    }
  };

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

  const toggleTodo = async (todo: PlanTodoOut) => {
    if (!plan) return;
    await updateTodo(plan.id, todo.id, { completed: !todo.completed });
    refetch();
  };

  const startEditTodo = (todo: PlanTodoOut) => {
    setEditingTodoId(todo.id);
    setEditingContent(todo.content);
  };

  const submitEditTodo = async (todo: PlanTodoOut) => {
    if (!plan || editingContent.trim() === "") {
      setEditingTodoId(null);
      return;
    }
    await updateTodo(plan.id, todo.id, { content: editingContent.trim() });
    setEditingTodoId(null);
    refetch();
  };

  const handleDeleteTodo = async (todo: PlanTodoOut) => {
    if (!plan) return;
    await deleteTodo(plan.id, todo.id);
    refetch();
  };

  const openAddTodo = (date: string) => {
    setAddingDate(date);
    setNewContent("");
  };

  const submitAddTodo = async (date: string) => {
    if (!plan || newContent.trim() === "") {
      setAddingDate(null);
      return;
    }
    await createTodo(plan.id, { todo_date: date, content: newContent.trim() });
    setAddingDate(null);
    setNewContent("");
    refetch();
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

  const grouped = todosByDate(plan.todos);
  const dates = dateRangeInclusive(plan.period_start, plan.period_end);
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
            onClick={startEdit}
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

        {/* Plan meta / edit form */}
        <div
          style={{
            padding: "20px 16px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            animation: "days-rise 320ms var(--ease-out) both",
          }}
        >
          {editing ? (
            <>
              <input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="Plan 이름"
                style={{
                  fontFamily: "var(--font-sans)",
                  fontWeight: 700,
                  fontSize: "var(--t-xl)",
                  color: "var(--ink-deep)",
                  border: "none",
                  borderBottom: "2px solid var(--sage-leaf)",
                  background: "transparent",
                  padding: "4px 0",
                  outline: "none",
                  width: "100%",
                }}
              />
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  type="date"
                  value={editStart}
                  onChange={(e) => setEditStart(e.target.value)}
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "var(--t-sm)",
                    border: "1px solid var(--line)",
                    borderRadius: 8,
                    padding: "6px 10px",
                    background: "var(--paper-pure)",
                    color: "var(--ink-body)",
                    outline: "none",
                    flex: 1,
                  }}
                />
                <span style={{ color: "var(--ink-soft)", fontSize: "var(--t-sm)" }}>~</span>
                <input
                  type="date"
                  value={editEnd}
                  onChange={(e) => setEditEnd(e.target.value)}
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "var(--t-sm)",
                    border: "1px solid var(--line)",
                    borderRadius: 8,
                    padding: "6px 10px",
                    background: "var(--paper-pure)",
                    color: "var(--ink-body)",
                    outline: "none",
                    flex: 1,
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  style={{
                    flex: 1,
                    padding: "10px 0",
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
                  onClick={submitEdit}
                  disabled={saving}
                  style={{
                    flex: 1,
                    padding: "10px 0",
                    background: "var(--sage-leaf)",
                    border: "none",
                    borderRadius: "var(--r-pill)",
                    fontFamily: "var(--font-sans)",
                    fontWeight: 600,
                    fontSize: "var(--t-sm)",
                    color: "var(--paper-pure)",
                    cursor: saving ? "wait" : "pointer",
                    opacity: saving ? 0.7 : 1,
                  }}
                >
                  저장
                </button>
              </div>
            </>
          ) : (
            <>
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
            </>
          )}

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

        {/* Date sections */}
        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {dates.map((date) => {
            const dateTodos = (grouped[date] ?? []).sort((a, b) => a.sequence - b.sequence);
            const datePercent = dateTodoProgress(plan.todos, date);

            return (
              <section
                key={date}
                aria-label={formatDateKo(date)}
                style={{
                  borderTop: "1px solid var(--line-faint)",
                  padding: "16px 16px 12px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                {/* Date header */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <h2
                    style={{
                      margin: 0,
                      fontFamily: "var(--font-sans)",
                      fontWeight: 600,
                      fontSize: "var(--t-sm)",
                      color: "var(--sage-forest)",
                    }}
                  >
                    {formatDateKo(date)}
                  </h2>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--t-xs)",
                      color: datePercent === 100 ? "var(--sage-leaf)" : "var(--ink-hint)",
                    }}
                  >
                    {datePercent}%
                  </span>
                </div>

                {/* Date progress bar */}
                <ProgressBar value={datePercent} />

                {/* Todos */}
                {dateTodos.length > 0 && (
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
                    {dateTodos.map((todo) => (
                      <li
                        key={todo.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          padding: "8px 4px",
                          borderRadius: 10,
                        }}
                      >
                        {/* Checkbox */}
                        <button
                          type="button"
                          aria-label={todo.completed ? "완료 취소" : "완료 처리"}
                          onClick={() => toggleTodo(todo)}
                          style={{
                            flexShrink: 0,
                            width: 22,
                            height: 22,
                            borderRadius: "50%",
                            border: `2px solid ${todo.completed ? "var(--sage-leaf)" : "var(--line-strong)"}`,
                            background: todo.completed ? "var(--sage-leaf)" : "transparent",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            padding: 0,
                            transition: "all var(--dur-2) var(--ease-out)",
                          }}
                        >
                          {todo.completed && (
                            <span style={{ color: "var(--paper-pure)", fontSize: 12, lineHeight: 1 }}>
                              ✓
                            </span>
                          )}
                        </button>

                        {/* Content (inline edit) */}
                        {editingTodoId === todo.id ? (
                          <input
                            ref={todoEditRef}
                            value={editingContent}
                            onChange={(e) => setEditingContent(e.target.value)}
                            onBlur={() => submitEditTodo(todo)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") submitEditTodo(todo);
                              if (e.key === "Escape") setEditingTodoId(null);
                            }}
                            style={{
                              flex: 1,
                              fontFamily: "var(--font-sans)",
                              fontSize: "var(--t-sm)",
                              border: "none",
                              borderBottom: "1px solid var(--sage-leaf)",
                              background: "transparent",
                              outline: "none",
                              padding: "2px 0",
                              color: "var(--ink-body)",
                            }}
                          />
                        ) : (
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={() => startEditTodo(todo)}
                            onKeyDown={(e) => e.key === "Enter" && startEditTodo(todo)}
                            style={{
                              flex: 1,
                              fontFamily: "var(--font-sans)",
                              fontSize: "var(--t-sm)",
                              color: todo.completed ? "var(--ink-hint)" : "var(--ink-body)",
                              textDecoration: todo.completed ? "line-through" : "none",
                              cursor: "text",
                              lineHeight: 1.5,
                            }}
                          >
                            {todo.content}
                          </span>
                        )}

                        {/* Delete */}
                        <button
                          type="button"
                          aria-label="할 일 삭제"
                          onClick={() => handleDeleteTodo(todo)}
                          style={{
                            flexShrink: 0,
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            color: "var(--ink-hint)",
                            fontSize: 14,
                            padding: "4px",
                            lineHeight: 1,
                            borderRadius: 6,
                            transition: "color var(--dur-1)",
                          }}
                        >
                          🗑
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {/* Add todo */}
                {addingDate === date ? (
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                    <input
                      ref={addInputRef}
                      value={newContent}
                      onChange={(e) => setNewContent(e.target.value)}
                      placeholder="할 일 내용"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") submitAddTodo(date);
                        if (e.key === "Escape") setAddingDate(null);
                      }}
                      style={{
                        flex: 1,
                        fontFamily: "var(--font-sans)",
                        fontSize: "var(--t-sm)",
                        border: "1px solid var(--line)",
                        borderRadius: 10,
                        padding: "8px 12px",
                        background: "var(--paper-pure)",
                        color: "var(--ink-body)",
                        outline: "none",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => submitAddTodo(date)}
                      style={{
                        padding: "8px 16px",
                        background: "var(--sage-leaf)",
                        color: "var(--paper-pure)",
                        border: "none",
                        borderRadius: 10,
                        fontFamily: "var(--font-sans)",
                        fontWeight: 600,
                        fontSize: "var(--t-sm)",
                        cursor: "pointer",
                      }}
                    >
                      추가
                    </button>
                    <button
                      type="button"
                      onClick={() => setAddingDate(null)}
                      style={{
                        padding: "8px 12px",
                        background: "var(--sage-cloud)",
                        color: "var(--ink-body)",
                        border: "none",
                        borderRadius: 10,
                        fontFamily: "var(--font-sans)",
                        fontSize: "var(--t-sm)",
                        cursor: "pointer",
                      }}
                    >
                      취소
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => openAddTodo(date)}
                    style={{
                      alignSelf: "flex-start",
                      background: "none",
                      border: "1px dashed var(--line)",
                      borderRadius: 10,
                      padding: "6px 14px",
                      fontFamily: "var(--font-sans)",
                      fontSize: "var(--t-xs)",
                      color: "var(--ink-hint)",
                      cursor: "pointer",
                      marginTop: 2,
                    }}
                  >
                    + todo 추가
                  </button>
                )}
              </section>
            );
          })}
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
      </div>
    </>
  );
}
