import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client from "../api/client";
import { postSSE } from "../api/sseClient";
import { Header } from "../components/layout/Header";
import { ChatBubble } from "../components/qna/ChatBubble";
import { ThinkingDots } from "../components/qna/ThinkingDots";
import { ChatInput } from "../components/qna/ChatInput";
import { ProgressBar } from "../components/days/ProgressBar";
import { ScheduleCard } from "../components/qna/ScheduleCard";

interface Message {
  role: "ai" | "user";
  text: string;
  sequence?: number;
}

interface PendingSchedule {
  period_start: string;
  period_end: string;
  situation: string;
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
  const [minReached, setMinReached] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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
        setMinReached(res.data.min_reached ?? false);
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

  const handleAccept = async (s: PendingSchedule) => {
    const key = scheduleKey(s);
    try {
      await client.post("/schedules", {
        period_start: s.period_start,
        period_end: s.period_end,
        situation: s.situation,
      });
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status !== 409) return;
    }
    setScheduleStatuses((prev) => new Map(prev).set(key, "accepted"));
  };

  const handleReject = (s: PendingSchedule) => {
    setScheduleStatuses((prev) =>
      new Map(prev).set(scheduleKey(s), "rejected"),
    );
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

  const totalQuestions = 5;

  if (done && accumulatedSchedules.length > 0) {
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
        <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-body)",
              marginBottom: 16,
            }}
          >
            이번 대화에서 나온 일정들을 확인해 주세요.
          </p>
          {accumulatedSchedules.map((s) => (
            <ScheduleCard
              key={scheduleKey(s)}
              schedule={s}
              status={scheduleStatuses.get(scheduleKey(s)) ?? "pending"}
              onAccept={() => handleAccept(s)}
              onReject={() => handleReject(s)}
            />
          ))}
        </div>
        {!allProcessed && (
          <div
            style={{ padding: "8px 16px 16px", background: "var(--paper-bone)" }}
          >
            <button
              type="button"
              onClick={() => navigate(`/diary/${date}`)}
              style={{
                width: "100%",
                padding: "12px",
                background: "var(--paper-pure)",
                border: "1px solid var(--ink-hint)",
                borderRadius: 12,
                fontFamily: "var(--font-sans)",
                fontSize: "var(--t-sm)",
                color: "var(--ink-meta)",
                cursor: "pointer",
              }}
            >
              건너뛰기
            </button>
          </div>
        )}
      </div>
    );
  }

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
            }}
          >
            {sequence} / {totalQuestions}
          </span>
        </div>
        <ProgressBar value={sequence} max={totalQuestions} />
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 16px",
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
            <ChatBubble role={msg.role}>{msg.text}</ChatBubble>
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
        style={{ padding: "8px 16px 16px", background: "var(--paper-bone)" }}
      >
        <ChatInput onSend={handleSend} disabled={thinking || done} />
      </div>
    </div>
  );
}
