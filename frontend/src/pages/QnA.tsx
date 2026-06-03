import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { postSSE } from "../api/sseClient";
import { Header } from "../components/layout/Header";
import { ChatBubble } from "../components/qna/ChatBubble";
import { ThinkingDots } from "../components/qna/ThinkingDots";
import { ChatInput } from "../components/qna/ChatInput";
import { ProgressBar } from "../components/days/ProgressBar";
import { ScheduleConfirmModal } from "../components/qna/ScheduleConfirmModal";
import type { PendingScheduleItem } from "../components/qna/ScheduleConfirmModal";
import { SuggestionChips } from "../components/qna/SuggestionChips";
import { finalizeQna, undoQna } from "../lib/qnaApi";
import { UndoConfirmModal } from "../components/qna/UndoConfirmModal";
import { AnswerEditBubble } from "../components/qna/AnswerEditBubble";

interface Message {
  role: "ai" | "user";
  text: string;
  sequence?: number;
}

interface PendingSchedule {
  period_start: string;
  period_end: string;
  situation: string;
  start_time?: string | null;
  end_time?: string | null;
}

function scheduleKey(s: PendingSchedule) {
  return `${s.period_start}_${s.period_end}_${s.situation}`;
}

export function Qna() {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [accumulatedSchedules, setAccumulatedSchedules] = useState<PendingSchedule[]>([]);
  const [scheduleStatuses, setScheduleStatuses] = useState<
    Map<string, "pending" | "accepted" | "rejected">
  >(new Map());
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sequence, setSequence] = useState(0);
  const [thinking, setThinking] = useState(false);
  const [done, setDone] = useState(false);
  const [loadingSteps, setLoadingSteps] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showContinueButtons, setShowContinueButtons] = useState(false);
  const [undoModal, setUndoModal] = useState<{ open: boolean; targetSequence: number }>({
    open: false,
    targetSequence: 0,
  });
  const [editing, setEditing] = useState<{ sequence: number; text: string } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);
  const [inputAreaHeight, setInputAreaHeight] = useState(100);
  const [inputAreaBottom, setInputAreaBottom] = useState<string>("var(--bottom-nav-h, 60px)");

  const STEP_LABELS: Record<string, string> = {
    schedules: "사용자 일정 읽어오는 중..",
    summaries: "사용자의 일기 읽어오는 중..",
    generating: "질문 생성 중..",
  };

  useEffect(() => {
    if (!date) return;
    postSSE(
      "/api/qna/start-stream",
      { diary_date: date },
      {
        onStatus: (step) => {
          const label = STEP_LABELS[step];
          if (label) setLoadingSteps((prev) => [...prev, label]);
        },
        onDone: (data) => {
          const d = data as {
            session_id: number;
            question: string;
            sequence: number;
            history?: { sequence: number; question: string; answer: string }[];
            pending_schedules?: PendingSchedule[];
            suggestions?: string[];
          };
          setLoadingSteps([]);
          setSessionId(d.session_id);
          setSequence(d.sequence);
          setSuggestions(d.suggestions ?? []);
          const history = d.history ?? [];
          const historyMsgs: Message[] = history.flatMap((h) => [
            { role: "ai" as const, text: h.question, sequence: h.sequence },
            { role: "user" as const, text: h.answer, sequence: h.sequence },
          ]);
          setMessages([...historyMsgs, { role: "ai", text: d.question, sequence: d.sequence }]);
          const pending: PendingSchedule[] = d.pending_schedules ?? [];
          if (pending.length > 0) {
            setAccumulatedSchedules((prev) => {
              const existingKeys = new Set(prev.map(scheduleKey));
              const newOnes = pending.filter((s) => !existingKeys.has(scheduleKey(s)));
              return newOnes.length > 0 ? [...prev, ...newOnes] : prev;
            });
          }
        },
        onError: () => {},
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const handleSend = async (text: string) => {
    if (!sessionId || thinking || done) return;
    const currentSeq = sequence;
    setMessages((m) => [...m, { role: "user", text, sequence: currentSeq }]);
    setInputValue("");
    setSuggestions([]);
    setThinking(true);
    try {
      const res = await client.post("/qna/answer", {
        session_id: sessionId,
        sequence: currentSeq,
        answer: text,
      });
      setThinking(false);
      const pending: PendingSchedule[] = res.data.pending_schedules ?? [];
      if (pending.length > 0) {
        setAccumulatedSchedules((prev) => {
          const existingKeys = new Set(prev.map(scheduleKey));
          const newOnes = pending.filter((s) => !existingKeys.has(scheduleKey(s)));
          return newOnes.length > 0 ? [...prev, ...newOnes] : prev;
        });
      }
      if (res.data.completed) {
        setDone(true);
        setMessages((m) => [
          ...m,
          { role: "ai", text: "오늘의 일기가 완성되었어요." },
        ]);
      } else {
        const nextSeq = res.data.sequence;
        setSequence(nextSeq);
        if (res.data.min_reached) setShowContinueButtons(true);
        setSuggestions(res.data.suggestions ?? []);
        setMessages((m) => [
          ...m,
          { role: "ai" as const, text: res.data.next_question, sequence: nextSeq },
        ]);
      }
    } catch {
      setThinking(false);
    }
  };

  const handleAccept = async (edited: PendingScheduleItem, original: PendingScheduleItem) => {
    const originalKey = scheduleKey(original as PendingSchedule);
    try {
      await client.post("/schedules", {
        period_start: edited.period_start,
        period_end: edited.period_end,
        start_time: edited.start_time ?? null,
        end_time: edited.end_time ?? null,
        situation: edited.situation,
      });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status !== 409) return;
    }
    setScheduleStatuses((prev) => new Map(prev).set(originalKey, "accepted"));
  };

  const handleReject = (s: PendingSchedule | PendingScheduleItem) => {
    setScheduleStatuses((prev) =>
      new Map(prev).set(scheduleKey(s as PendingSchedule), "rejected"),
    );
  };

  const openUndoModal = (seq: number) => {
    if (thinking || done) return;
    setUndoModal({ open: true, targetSequence: seq });
  };

  const handleUndoConfirm = async (mode: 'keep' | 'discard') => {
    if (!sessionId) return;
    setUndoModal((s) => ({ ...s, open: false }));

    if (mode === 'keep') {
      const targetSeq = undoModal.targetSequence;
      const userMsg = messages.find((m) => m.role === 'user' && m.sequence === targetSeq);
      setEditing({ sequence: targetSeq, text: userMsg?.text ?? '' });
      return;
    }

    setThinking(true);
    try {
      const res = await undoQna(sessionId, undoModal.targetSequence, 'discard');
      setThinking(false);
      setSequence(undoModal.targetSequence);
      setShowContinueButtons(false);
      setInputValue('');
      setSuggestions([]);

      // Trim from target user message onwards; target AI question stays visible
      setMessages((prev) => {
        const idx = prev.findIndex(
          (m) => m.role === 'user' && m.sequence === undoModal.targetSequence
        );
        return idx >= 0 ? prev.slice(0, idx) : prev;
      });

      if (res.removed_schedule_keys.length > 0) {
        const removedSet = new Set(res.removed_schedule_keys);
        setAccumulatedSchedules((prev) =>
          prev.filter((s) => !removedSet.has(`${s.period_start}|${s.period_end}|${s.situation}`))
        );
      }
    } catch {
      setThinking(false);
    }
  };

  const handleEditSave = async () => {
    if (!sessionId || !editing) return;
    setThinking(true);
    try {
      const res = await undoQna(sessionId, editing.sequence, 'keep', editing.text);
      setThinking(false);
      setMessages((prev) =>
        prev.map((m) => {
          if (m.role === 'user' && m.sequence === editing.sequence) return { ...m, text: editing.text };
          if (m.role === 'ai' && m.sequence === res.sequence) return { ...m, text: res.question };
          return m;
        })
      );
      setSequence(res.sequence);
      setSuggestions(res.suggestions);
      setShowContinueButtons(false);

      if (res.removed_schedule_keys.length > 0) {
        const removedSet = new Set(res.removed_schedule_keys);
        setAccumulatedSchedules((prev) =>
          prev.filter((s) => !removedSet.has(`${s.period_start}|${s.period_end}|${s.situation}`))
        );
      }
      if (res.pending_schedules.length > 0) {
        setAccumulatedSchedules((prev) => {
          const existingKeys = new Set(prev.map(scheduleKey));
          const newOnes = (res.pending_schedules as PendingSchedule[]).filter(
            (s) => !existingKeys.has(scheduleKey(s))
          );
          return newOnes.length > 0 ? [...prev, ...newOnes] : prev;
        });
      }
      setEditing(null);
    } catch {
      setThinking(false);
    }
  };

  const handleEditCancel = () => setEditing(null);

  const handleFinalize = async () => {
    if (!sessionId || thinking || done) return;
    setThinking(true);
    try {
      await finalizeQna(sessionId);
      setThinking(false);
      setDone(true);
      setSuggestions([]);
      setShowContinueButtons(false);
      setMessages((m) => [
        ...m,
        { role: "ai", text: "오늘의 일기가 완성되었어요." },
      ]);
    } catch {
      setThinking(false);
    }
  };

  const allProcessed =
    accumulatedSchedules.length > 0 &&
    accumulatedSchedules.every((s) => {
      const st = scheduleStatuses.get(scheduleKey(s));
      return st === "accepted" || st === "rejected";
    });

  useEffect(() => {
    if (!done) return;
    if (accumulatedSchedules.length === 0) {
      const t = setTimeout(() => navigate(`/diary/${date}`), 1200);
      return () => clearTimeout(t);
    }
    if (allProcessed) {
      const t = setTimeout(() => navigate(`/diary/${date}`), 600);
      return () => clearTimeout(t);
    }
  }, [done, accumulatedSchedules.length, allProcessed, navigate, date]);

  useEffect(() => {
    const el = inputAreaRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => {
      setInputAreaHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    const update = () => {
      const keyboardHeight = Math.max(
        0,
        window.innerHeight - vv.height - vv.offsetTop,
      );
      const bnhStr = getComputedStyle(document.documentElement).getPropertyValue("--bottom-nav-h");
      const bnhPx = parseFloat(bnhStr) || 60;
      if (keyboardHeight > 10) {
        setInputAreaBottom(`${Math.max(bnhPx, keyboardHeight)}px`);
      } else {
        setInputAreaBottom("var(--bottom-nav-h, 60px)");
      }
    };
    vv.addEventListener("resize", update);
    vv.addEventListener("scroll", update);
    return () => {
      vv.removeEventListener("resize", update);
      vv.removeEventListener("scroll", update);
    };
  }, []);

  const totalQuestions = 5;
  const progressValue = Math.min(sequence, totalQuestions);
  const extraQuestions = sequence > totalQuestions ? sequence - totalQuestions : 0;

  const currentModalSchedule = !thinking
    ? accumulatedSchedules.find(
        (s) => {
          const st = scheduleStatuses.get(scheduleKey(s));
          return st === undefined || st === "pending";
        }
      ) ?? null
    : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: "calc(100dvh - 80px)",
        animation: "days-fade-in 300ms var(--ease-out) both",
      }}
    >
      <Header title={date ?? ""} showBack />
      <div style={{ padding: "4px 16px 8px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 6,
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-xs)",
              color: "var(--ink-meta)",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            {progressValue} / {totalQuestions}
            {extraQuestions > 0 && (
              <span
                style={{
                  color: "var(--sage-leaf)",
                  fontFamily: "var(--font-sans)",
                  fontSize: "var(--t-xs)",
                  fontWeight: 600,
                }}
              >
                +{extraQuestions}
              </span>
            )}
          </span>
        </div>
        <ProgressBar value={progressValue} max={totalQuestions} />
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: `8px 16px ${inputAreaHeight}px`,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {loadingSteps.map((label, i) => (
          <div
            key={i}
            style={{
              textAlign: "center",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-meta)",
              animation: "days-rise 240ms var(--ease-out) both",
            }}
          >
            {label}
          </div>
        ))}
        {messages.map((msg, i) => (
          <div key={i}>
            {editing?.sequence === msg.sequence && msg.role === 'user' ? (
              <AnswerEditBubble
                value={editing.text}
                onChange={(v) => setEditing((e) => e ? { ...e, text: v } : e)}
                onSave={handleEditSave}
                onCancel={handleEditCancel}
                saving={thinking}
              />
            ) : (
              <ChatBubble
                role={msg.role}
                onUndo={msg.role === 'user' && msg.sequence !== undefined ? () => openUndoModal(msg.sequence!) : undefined}
                undoDisabled={thinking || done || editing !== null}
              >
                {msg.text}
              </ChatBubble>
            )}
          </div>
        ))}
        {thinking && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <ThinkingDots visible />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div
        ref={inputAreaRef}
        style={{
          position: "fixed",
          left: "50%",
          transform: "translateX(-50%)",
          width: "100%",
          maxWidth: 480,
          bottom: inputAreaBottom,
          zIndex: 90,
          background: "var(--paper-bone)",
          padding: "8px 16px 16px",
          boxSizing: "border-box",
        } as React.CSSProperties}
      >
        {showContinueButtons && !done && (
          <div
            style={{
              marginBottom: 12,
              animation: "days-rise 240ms var(--ease-out) both",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "var(--t-sm)",
                color: "var(--ink-meta)",
                textAlign: "center",
                margin: "0 0 10px",
              }}
            >
              더 이야기해 볼까요?
            </p>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={() => setShowContinueButtons(false)}
                style={{
                  flex: 1,
                  padding: "11px 0",
                  borderRadius: 999,
                  border: "1.5px solid var(--sage-leaf)",
                  background: "transparent",
                  fontFamily: "var(--font-sans)",
                  fontSize: "var(--t-sm)",
                  color: "var(--sage-forest)",
                  fontWeight: 500,
                  cursor: "pointer",
                  transition: "background var(--dur-1) var(--ease-out)",
                }}
              >
                계속 이어가기
              </button>
              <button
                type="button"
                onClick={handleFinalize}
                disabled={thinking}
                style={{
                  flex: 1,
                  padding: "11px 0",
                  borderRadius: 999,
                  border: 0,
                  background: thinking ? "var(--sage-mist)" : "var(--sage-leaf)",
                  fontFamily: "var(--font-sans)",
                  fontSize: "var(--t-sm)",
                  color: "var(--paper-pure)",
                  fontWeight: 600,
                  cursor: thinking ? "not-allowed" : "pointer",
                  transition: "background var(--dur-1) var(--ease-out)",
                }}
              >
                여기서 마무리
              </button>
            </div>
          </div>
        )}
        <SuggestionChips
          suggestions={suggestions}
          onPick={(t) => setInputValue(t)}
          disabled={thinking || done || editing !== null}
        />
        <ChatInput
          onSend={handleSend}
          disabled={thinking || done || editing !== null}
          value={inputValue}
          onChange={setInputValue}
        />
      </div>
      <UndoConfirmModal
        open={undoModal.open}
        onClose={() => setUndoModal((s) => ({ ...s, open: false }))}
        onConfirm={handleUndoConfirm}
        targetSequence={undoModal.targetSequence}
      />
      <ScheduleConfirmModal
        open={!!currentModalSchedule}
        schedule={currentModalSchedule}
        onAccept={(edited) => handleAccept(edited, currentModalSchedule!)}
        onReject={() => currentModalSchedule && handleReject(currentModalSchedule)}
      />
    </div>
  );
}
