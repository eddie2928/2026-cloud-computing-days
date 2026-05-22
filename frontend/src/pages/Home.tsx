import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import client from "../api/client";
import { DiaryDetailModal } from "../components/DiaryDetailModal";
import { ChatSessionModal } from "../components/ChatSessionModal";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CalendarEntry {
  date: string;
  emotion: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const TODAY_ISO = new Date().toISOString().slice(0, 10);

const COMBO_TIERS = [
  {
    idx: 0,
    min: 0,
    max: 0,
    label: "시작 전",
    greeting: "오늘이 첫날이에요.",
    glowAlpha: 0.1,
    ringAlpha: 0.35,
    ringScale: 1.0,
    accent: "var(--ink-soft)",
    petalGain: 0,
  },
  {
    idx: 1,
    min: 1,
    max: 2,
    label: "새싹",
    greeting: "새싹이 돋아나요.",
    glowAlpha: 0.16,
    ringAlpha: 0.42,
    ringScale: 1.02,
    accent: "var(--gold-soft)",
    petalGain: 0,
  },
  {
    idx: 2,
    min: 3,
    max: 6,
    label: "데이지 한 송이",
    greeting: "벌써 한 송이 피었어요.",
    glowAlpha: 0.24,
    ringAlpha: 0.5,
    ringScale: 1.04,
    accent: "var(--gold-warm)",
    petalGain: 1,
  },
  {
    idx: 3,
    min: 7,
    max: 13,
    label: "활짝 핀 일주일",
    greeting: "한 주 동안 함께해주셨어요.",
    glowAlpha: 0.34,
    ringAlpha: 0.6,
    ringScale: 1.07,
    accent: "var(--gold)",
    petalGain: 2,
  },
  {
    idx: 4,
    min: 14,
    max: 29,
    label: "황금빛 2주",
    greeting: "2주, 흐름이 잡혔네요.",
    glowAlpha: 0.46,
    ringAlpha: 0.72,
    ringScale: 1.1,
    accent: "var(--gold)",
    petalGain: 3,
  },
  {
    idx: 5,
    min: 30,
    max: 99,
    label: "한 달의 결",
    greeting: "한 달째, 매일이 일기예요.",
    glowAlpha: 0.58,
    ringAlpha: 0.85,
    ringScale: 1.14,
    accent: "var(--gold-deep)",
    petalGain: 4,
  },
  {
    idx: 6,
    min: 100,
    max: Infinity,
    label: "아카이브",
    greeting: "백 일을 넘었어요.",
    glowAlpha: 0.7,
    ringAlpha: 0.95,
    ringScale: 1.18,
    accent: "var(--gold-deep)",
    petalGain: 5,
  },
] as const;

type Tier = (typeof COMBO_TIERS)[number];

function tierFor(n: number): Tier {
  return (COMBO_TIERS.find((t) => n >= t.min && n <= t.max) ??
    COMBO_TIERS[0]) as Tier;
}

function computeStreak(savedDates: string[], todayISO: string): number {
  const dateSet = new Set(savedDates);
  let streak = 0;
  const d = new Date(todayISO + "T00:00:00");
  if (!dateSet.has(todayISO)) d.setDate(d.getDate() - 1);
  while (dateSet.has(d.toISOString().slice(0, 10))) {
    streak++;
    d.setDate(d.getDate() - 1);
  }
  return streak;
}

// ─── StageDaisy ───────────────────────────────────────────────────────────────

function StageDaisy({ size = 120, tier }: { size?: number; tier: Tier }) {
  const petals = 6 + Math.min(tier.petalGain * 2, 8);
  const petal =
    "M 12 11 C 9.5 11, 7.6 8.5, 7.6 5.6 C 7.6 2.4, 9.5 0.4, 12 0.4 C 14.5 0.4, 16.4 2.4, 16.4 5.6 C 16.4 8.5, 14.5 11, 12 11 Z";
  const angles = Array.from({ length: petals }, (_, i) => (360 / petals) * i);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      style={{
        filter: `drop-shadow(0 4px 8px rgba(94,70,30,${0.1 + tier.glowAlpha * 0.3}))`,
        animation: "home-float 6s ease-in-out infinite",
      }}
    >
      <g fill="#FFFFFF" stroke={tier.accent} strokeWidth="0.5">
        {angles.map((a, i) => (
          <path key={i} d={petal} transform={`rotate(${a} 12 12)`} />
        ))}
      </g>
      <circle
        cx="12"
        cy="12"
        r="4"
        fill={tier.accent}
        stroke="#A7842D"
        strokeWidth="0.4"
      />
      {tier.petalGain >= 3 && (
        <circle cx="12" cy="12" r="1.6" fill="#FFFFFF" opacity="0.7" />
      )}
    </svg>
  );
}

// ─── ComboStage ───────────────────────────────────────────────────────────────

function ComboStage({ combo }: { combo: number }) {
  const tier = tierFor(combo);
  const stageSize = 280;
  const ringSize = stageSize * 0.88;
  const slotSize = stageSize * 0.66;

  return (
    <div
      style={{
        position: "relative",
        width: stageSize,
        height: stageSize,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Ambient floor glow */}
      <div
        style={{
          position: "absolute",
          inset: -40,
          background: `radial-gradient(ellipse at 50% 62%, rgba(214,166,70,${tier.glowAlpha * 0.65}) 0%, rgba(214,166,70,${tier.glowAlpha * 0.2}) 32%, transparent 62%)`,
          filter: "blur(2px)",
          transition: "background var(--dur-3) var(--ease-out)",
          pointerEvents: "none",
        }}
      />

      {/* Outer ring */}
      <div
        style={{
          position: "absolute",
          width: ringSize,
          height: ringSize,
          borderRadius: "50%",
          border: "1px solid var(--gold-soft)",
          opacity: tier.ringAlpha * 0.55,
          animation: "home-ring-pulse 5s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />

      {/* Inner dashed ring */}
      <div
        style={{
          position: "absolute",
          width: ringSize * 0.78,
          height: ringSize * 0.78,
          borderRadius: "50%",
          border: "1px dashed var(--gold-warm)",
          opacity: tier.ringAlpha * 0.5,
          transform: `scale(${tier.ringScale * 0.98})`,
          transition:
            "opacity var(--dur-3), transform var(--dur-3) var(--ease-out)",
          pointerEvents: "none",
        }}
      />

      {/* Plinth disc */}
      <div
        style={{
          position: "absolute",
          width: ringSize * 0.66,
          height: ringSize * 0.66,
          borderRadius: "50%",
          background:
            "radial-gradient(circle at 50% 35%, var(--paper-mist) 0%, var(--paper-cream) 55%, var(--paper-warm) 100%)",
          border: "1px solid var(--line-faint)",
          boxShadow: `inset 0 -8px 16px rgba(94,70,30,0.07), 0 1px 0 var(--paper-bone), 0 0 30px rgba(214,166,70,${tier.glowAlpha * 0.4})`,
          transition: "box-shadow var(--dur-3) var(--ease-out)",
        }}
      />

      {/* Floor shadow */}
      <div
        style={{
          position: "absolute",
          bottom: stageSize * 0.18,
          width: slotSize * 0.7,
          height: 18,
          borderRadius: "50%",
          background:
            "radial-gradient(ellipse, rgba(94,70,30,0.25), transparent 70%)",
          filter: "blur(3px)",
          pointerEvents: "none",
        }}
      />

      {/* Daisy character */}
      <div
        style={{
          position: "relative",
          width: slotSize,
          height: slotSize,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <StageDaisy size={slotSize * 0.75} tier={tier} />
      </div>

      {/* Tier badge */}
      <div
        style={{
          position: "absolute",
          top: 8,
          right: 8,
          padding: "4px 10px",
          borderRadius: 999,
          background: "var(--paper-bone)",
          border: "1px solid var(--line)",
          font: "500 10px/1 var(--font-sans)",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--gold-deep)",
          boxShadow: "0 1px 2px rgba(94,70,30,0.06)",
          animation: "days-fade-in 400ms var(--ease-out) 600ms both",
          whiteSpace: "nowrap",
        }}
      >
        {tier.label}
      </div>
    </div>
  );
}

// ─── ComboReadout ─────────────────────────────────────────────────────────────

function ComboReadout({ combo }: { combo: number }) {
  const tier = tierFor(combo);
  const nextMilestone = [3, 7, 14, 30, 100, 365].find((m) => m > combo) ?? 365;
  const remaining = nextMilestone - combo;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        animation: "days-rise 500ms var(--ease-out) 120ms both",
      }}
    >
      <div
        style={{
          font: "500 11px/1 var(--font-sans)",
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--gold-deep)",
        }}
      >
        days · 콤보
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
        <span
          style={{
            font: "400 88px/0.95 var(--font-serif)",
            fontStyle: "italic",
            letterSpacing: "-0.03em",
            background: `linear-gradient(180deg, var(--ink-coffee) 0%, ${tier.accent} 130%)`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          {combo}
        </span>
        <span
          style={{
            font: "500 16px/1 var(--font-sans)",
            color: "var(--ink-bark)",
          }}
        >
          일 연속
        </span>
      </div>

      <div
        style={{
          font: "400 17px/1.5 var(--font-serif)",
          color: "var(--ink-walnut)",
          maxWidth: 340,
        }}
      >
        {tier.greeting}
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          maxWidth: 340,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
          }}
        >
          <span
            style={{
              font: "500 11px/1 var(--font-mono)",
              color: "var(--ink-stone)",
              letterSpacing: "0.05em",
            }}
          >
            다음 마일스톤
          </span>
          <span
            style={{
              font: "500 12px/1 var(--font-mono)",
              color: "var(--ink-walnut)",
            }}
          >
            {combo}{" "}
            <span style={{ color: "var(--ink-stone)" }}>/ {nextMilestone}</span>
          </span>
        </div>
        <div
          style={{
            height: 4,
            background: "var(--paper-warm)",
            borderRadius: 999,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${Math.min(100, (combo / nextMilestone) * 100)}%`,
              background: `linear-gradient(90deg, var(--gold-warm), ${tier.accent})`,
              borderRadius: 999,
              transition: "width var(--dur-3) var(--ease-out)",
            }}
          />
        </div>
        <div
          style={{
            font: "400 12px/1.4 var(--font-sans)",
            color: "var(--ink-stone)",
          }}
        >
          {remaining > 0
            ? `${remaining}일만 더 이어가면 ${nextMilestone}일이에요.`
            : "도착했어요."}
        </div>
      </div>
    </div>
  );
}

// ─── SearchBar ────────────────────────────────────────────────────────────────

function SearchBar({
  savedDates,
  onDateClick,
}: {
  savedDates: string[];
  onDateClick: (date: string) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const results = useMemo(() => {
    if (!q.trim()) return [];
    return savedDates.filter((d) => d.includes(q.trim())).slice(0, 6);
  }, [q, savedDates]);

  function highlight(text: string) {
    const needle = q.trim();
    if (!needle) return <>{text}</>;
    const i = text.toLowerCase().indexOf(needle.toLowerCase());
    if (i < 0) return <>{text}</>;
    return (
      <>
        {text.slice(0, i)}
        <mark
          style={{
            background: "var(--gold-glow)",
            color: "var(--ink-coffee)",
            padding: "0 2px",
            borderRadius: 3,
          }}
        >
          {text.slice(i, i + needle.length)}
        </mark>
        {text.slice(i + needle.length)}
      </>
    );
  }

  return (
    <div ref={wrapRef} style={{ position: "relative", flex: 1, maxWidth: 420 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "10px 14px",
          background: open || q ? "var(--paper-bone)" : "var(--paper-mist)",
          border: "1px solid",
          borderColor: open || q ? "var(--gold)" : "var(--line)",
          borderRadius: 12,
          boxShadow: open || q ? "0 0 0 4px rgba(214,166,70,0.18)" : "none",
          transition:
            "border-color var(--dur-1), box-shadow var(--dur-1), background var(--dur-1)",
        }}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--ink-stone)", flexShrink: 0 }}
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="일기 검색 · 날짜"
          style={{
            flex: 1,
            border: 0,
            background: "transparent",
            outline: "none",
            font: "400 14px/1 var(--font-sans)",
            color: "var(--ink-coffee)",
          }}
        />
        {q && (
          <button
            onClick={() => {
              setQ("");
              setOpen(false);
            }}
            style={{
              background: "transparent",
              border: 0,
              cursor: "pointer",
              padding: 2,
              display: "flex",
              color: "var(--ink-stone)",
            }}
          >
            <img src="/brand/icons/close.svg" width="14" height="14" alt="" />
          </button>
        )}
      </div>

      {open && q.trim() && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            background: "var(--paper-bone)",
            border: "1px solid var(--line)",
            borderRadius: 14,
            boxShadow:
              "0 8px 20px -6px rgba(94,70,30,0.14), 0 2px 4px rgba(94,70,30,0.06)",
            padding: 6,
            zIndex: 20,
            animation: "days-rise 240ms var(--ease-out) both",
            maxHeight: 360,
            overflow: "auto",
          }}
        >
          {results.length === 0 ? (
            <div
              style={{
                padding: "18px 14px",
                font: "400 13px/1.4 var(--font-sans)",
                color: "var(--ink-stone)",
              }}
            >
              일치하는 일기가 없어요.
            </div>
          ) : (
            results.map((date, i) => (
              <button
                key={date}
                onClick={() => {
                  onDateClick(date);
                  setOpen(false);
                  setQ("");
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "var(--paper-mist)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "transparent")
                }
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 12px",
                  background: "transparent",
                  border: 0,
                  borderRadius: 10,
                  cursor: "pointer",
                  transition: "background var(--dur-1)",
                  animation: `days-fade-in 240ms var(--ease-out) ${i * 40}ms both`,
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 999,
                    background: "var(--gold-warm)",
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    font: "500 14px/1 var(--font-mono)",
                    color: "var(--ink-walnut)",
                  }}
                >
                  {highlight(date)}
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ─── MiniCalendar ─────────────────────────────────────────────────────────────

function MiniCalendar({
  year,
  month,
  todayISO,
  savedDates,
  view,
  onDateClick,
}: {
  year: number;
  month: number;
  todayISO: string;
  savedDates: string[];
  view: "week" | "month";
  onDateClick: (date: string) => void;
}) {
  const isWeek = view === "week";

  const cells = useMemo<(Date | null)[]>(() => {
    if (isWeek) {
      const t = new Date(todayISO + "T00:00:00");
      const sunday = new Date(t);
      sunday.setDate(t.getDate() - t.getDay());
      return Array.from({ length: 7 }, (_, i) => {
        const d = new Date(sunday);
        d.setDate(sunday.getDate() + i);
        return d;
      });
    }
    const lastDay = new Date(year, month, 0).getDate();
    const startDow = new Date(year, month - 1, 1).getDay();
    const out: (Date | null)[] = [];
    for (let i = 0; i < startDow; i++) out.push(null);
    for (let d = 1; d <= lastDay; d++) out.push(new Date(year, month - 1, d));
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [year, month, todayISO, isWeek]);

  const isoOf = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  const monthName = [
    "1월",
    "2월",
    "3월",
    "4월",
    "5월",
    "6월",
    "7월",
    "8월",
    "9월",
    "10월",
    "11월",
    "12월",
  ][month - 1];

  const weekRangeLabel = (() => {
    if (!isWeek) return null;
    const sun = cells[0] as Date;
    const sat = cells[6] as Date;
    return `${sun.getMonth() + 1}월 ${sun.getDate()}일 – ${sat.getMonth() + 1}월 ${sat.getDate()}일`;
  })();

  const entriesInScope = isWeek
    ? (cells as (Date | null)[]).filter(
        (d) => d !== null && savedDates.includes(isoOf(d as Date)),
      ).length
    : savedDates.filter((d) =>
        d.startsWith(`${year}-${String(month).padStart(2, "0")}`),
      ).length;

  const cellMinHeight = isWeek ? 64 : undefined;

  return (
    <div
      style={{
        background: "var(--paper-cream)",
        border: "1px solid var(--line)",
        borderRadius: 18,
        padding: isWeek ? "22px 24px" : 20,
        boxShadow:
          "0 2px 6px rgba(94,70,30,0.08), 0 1px 2px rgba(94,70,30,0.04)",
        display: "flex",
        flexDirection: "column",
        gap: isWeek ? 16 : 12,
        animation: "days-rise 500ms var(--ease-out) 280ms both",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div
            style={{
              font: "500 11px/1 var(--font-sans)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--gold-deep)",
            }}
          >
            {isWeek ? "이번 주" : "이번 달"}
          </div>
          <div
            style={{
              font: "400 22px/1.1 var(--font-serif)",
              color: "var(--ink-coffee)",
              letterSpacing: "-0.01em",
            }}
          >
            {isWeek ? weekRangeLabel : `${year}년 ${monthName}`}
          </div>
        </div>
        <div
          style={{
            font: "500 11px/1 var(--font-mono)",
            color: "var(--ink-stone)",
          }}
        >
          {entriesInScope} entries
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: isWeek ? 8 : 3,
        }}
      >
        {["일", "월", "화", "수", "목", "금", "토"].map((d, i) => (
          <div
            key={d}
            style={{
              font: "500 10px/1 var(--font-mono)",
              color: i === 0 ? "var(--clay)" : "var(--ink-stone)",
              textAlign: "center",
              padding: "4px 0",
              letterSpacing: "0.06em",
            }}
          >
            {d}
          </div>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: isWeek ? 8 : 4,
        }}
      >
        {cells.map((d, i) => {
          if (d === null) return <div key={i} />;
          const dateISO = isoOf(d);
          const isSaved = savedDates.includes(dateISO);
          const isToday = dateISO === todayISO;
          const isFuture = dateISO > todayISO;
          const dow = d.getDay();
          const numColor = isFuture
            ? "var(--ink-soft)"
            : dow === 0
              ? "var(--clay)"
              : "var(--ink-walnut)";
          const clickable = isSaved || isToday;
          return (
            <button
              key={i}
              disabled={!clickable}
              onClick={() => clickable && onDateClick(dateISO)}
              onMouseEnter={(e) => {
                if (clickable)
                  e.currentTarget.style.background = isToday
                    ? "var(--gold-glow)"
                    : "var(--paper-mist)";
              }}
              onMouseLeave={(e) => {
                if (clickable)
                  e.currentTarget.style.background = isToday
                    ? "var(--gold-mist)"
                    : isWeek && isSaved
                      ? "var(--paper-bone)"
                      : "transparent";
              }}
              style={{
                aspectRatio: isWeek ? undefined : "1",
                minHeight: cellMinHeight,
                background: isToday
                  ? "var(--gold-mist)"
                  : isWeek && isSaved
                    ? "var(--paper-bone)"
                    : "transparent",
                border: isToday
                  ? "1.5px solid var(--gold)"
                  : isWeek
                    ? "1px solid var(--line-faint)"
                    : "1px solid transparent",
                borderRadius: isWeek ? 12 : 8,
                padding: isWeek ? "10px 6px" : 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: isWeek ? "space-between" : "center",
                cursor: clickable ? "pointer" : "default",
                font: isWeek
                  ? "500 16px/1 var(--font-mono)"
                  : "500 11px/1 var(--font-mono)",
                color: numColor,
                transition: "background var(--dur-1)",
                gap: isWeek ? 8 : 2,
                position: "relative",
              }}
            >
              <span>{d.getDate()}</span>
              <span
                style={{
                  width: isWeek ? 6 : 4,
                  height: isWeek ? 6 : 4,
                  borderRadius: 999,
                  background: isSaved ? "var(--gold-warm)" : "transparent",
                  transition: "background var(--dur-1)",
                }}
              />
            </button>
          );
        })}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          paddingTop: 4,
          borderTop: "1px solid var(--line-faint)",
          font: "400 11px/1 var(--font-sans)",
          color: "var(--ink-stone)",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: 999,
              background: "var(--gold-warm)",
            }}
          />{" "}
          작성
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              border: "1.5px solid var(--gold)",
              background: "var(--gold-mist)",
            }}
          />{" "}
          오늘
        </span>
      </div>
    </div>
  );
}

// ─── Home ─────────────────────────────────────────────────────────────────────

export function Home() {
  const [entries, setEntries] = useState<CalendarEntry[]>([]);
  const [userName, setUserName] = useState("");
  const [calendarView] = useState<"week" | "month">("week");
  const [selectedDiaryDate, setSelectedDiaryDate] = useState<string | null>(
    null,
  );
  const [selectedNewDate, setSelectedNewDate] = useState<string | null>(null);

  const savedDates = useMemo(() => entries.map((e) => e.date), [entries]);
  const todayWritten = savedDates.includes(TODAY_ISO);
  const combo = useMemo(
    () => computeStreak(savedDates, TODAY_ISO),
    [savedDates],
  );
  const tier = tierFor(combo);

  const today = new Date(TODAY_ISO + "T00:00:00");
  const dowKo = ["일", "월", "화", "수", "목", "금", "토"][today.getDay()];
  const dateLabel = `${today.getMonth() + 1}월 ${today.getDate()}일 ${dowKo}요일`;
  const greetingLine = todayWritten
    ? `${userName}님, 오늘도 일기를 남기셨네요.`
    : `${userName}님, 오늘은 어떤 하루였나요?`;

  // Fetch last 4 months to compute streak accurately
  useEffect(() => {
    const months: string[] = [];
    for (let i = 0; i < 4; i++) {
      const d = new Date();
      d.setMonth(d.getMonth() - i);
      months.push(
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
      );
    }
    Promise.all(
      months.map((m) =>
        client
          .get("/calendar", { params: { month: m } })
          .catch(() => ({ data: { entries: [] } })),
      ),
    ).then((results) => {
      setEntries(results.flatMap((r) => r.data.entries as CalendarEntry[]));
    });
  }, []);

  useEffect(() => {
    client
      .get("/profile")
      .then((r) => {
        if (r.data.nickname) setUserName(r.data.nickname);
      })
      .catch(() => {});
  }, []);

  const handleDateClick = useCallback(
    (dateISO: string) => {
      if (savedDates.includes(dateISO)) {
        setSelectedDiaryDate(dateISO);
      } else if (dateISO <= TODAY_ISO) {
        setSelectedNewDate(dateISO);
      }
    },
    [savedDates],
  );

  const handleDiaryUpdated = useCallback(() => {
    setEntries((prev) => [...prev]);
  }, []);

  const handleChatComplete = useCallback(async () => {
    if (!selectedNewDate) return;
    const date = selectedNewDate;
    setSelectedNewDate(null);
    try {
      const month = date.slice(0, 7);
      const resp = await client.get("/calendar", { params: { month } });
      setEntries((prev) => {
        const others = prev.filter((e) => !e.date.startsWith(month));
        return [...others, ...(resp.data.entries as CalendarEntry[])];
      });
    } catch {
      // ignore
    }
    setSelectedDiaryDate(date);
  }, [selectedNewDate]);

  return (
    <div
      style={{
        padding: "32px 48px 48px",
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        gap: 28,
        overflow: "auto",
        backgroundImage:
          "radial-gradient(circle at 1px 1px, rgba(221, 207, 177, 0.32) 1px, transparent 0)",
        backgroundSize: "24px 24px",
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 32,
          paddingBottom: 8,
          animation: "days-fade-in 400ms var(--ease-out) both",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            flex: 1,
            minWidth: 0,
          }}
        >
          <div
            style={{
              font: "500 11px/1 var(--font-sans)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "var(--gold-deep)",
            }}
          >
            {dateLabel} · {TODAY_ISO}
          </div>
          <h1
            style={{
              margin: 0,
              font: "400 32px/1.2 var(--font-serif)",
              color: "var(--ink-coffee)",
              letterSpacing: "-0.015em",
            }}
          >
            {greetingLine}
          </h1>
        </div>
        <SearchBar savedDates={savedDates} onDateClick={handleDateClick} />
      </header>

      {/* Hero */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "1fr auto",
          gap: 40,
          alignItems: "center",
          padding: "36px 44px",
          background: "var(--paper-cream)",
          border: "1px solid var(--line)",
          borderRadius: 24,
          boxShadow:
            "0 2px 6px rgba(94,70,30,0.08), 0 1px 2px rgba(94,70,30,0.04)",
          position: "relative",
          overflow: "hidden",
          animation: "days-rise 600ms var(--ease-out) 80ms both",
        }}
      >
        {/* Warm halo behind stage */}
        <div
          style={{
            position: "absolute",
            right: -120,
            top: -80,
            width: 480,
            height: 480,
            borderRadius: "50%",
            background: `radial-gradient(circle, rgba(244,229,182,${0.35 + tier.glowAlpha * 0.45}) 0%, transparent 65%)`,
            pointerEvents: "none",
            transition: "background var(--dur-3) var(--ease-out)",
          }}
        />

        {/* Left: readout + CTA */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 24,
            minWidth: 0,
            position: "relative",
          }}
        >
          <ComboReadout combo={combo} />

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12,
              alignItems: "flex-start",
            }}
          >
            {!todayWritten && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  font: "500 12px/1 var(--font-sans)",
                  color: "var(--ink-bark)",
                  letterSpacing: "0.02em",
                  animation: "days-fade-in 400ms var(--ease-out) 380ms both",
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 999,
                    background: "var(--gold-warm)",
                    animation: "days-dot-pulse 1.4s var(--ease-out) infinite",
                  }}
                />
                오늘 일기는 아직 비어있어요.
              </div>
            )}

            <div style={{ position: "relative", display: "inline-flex" }}>
              {!todayWritten && (
                <div
                  style={{
                    position: "absolute",
                    inset: -10,
                    borderRadius: 999,
                    background:
                      "radial-gradient(ellipse at 50% 60%, rgba(214,166,70,0.32) 0%, rgba(214,166,70,0.10) 50%, transparent 75%)",
                    filter: "blur(2px)",
                    pointerEvents: "none",
                    zIndex: 0,
                  }}
                />
              )}
              {!todayWritten ? (
                <button
                  onClick={() => setSelectedNewDate(TODAY_ISO)}
                  onMouseDown={(e) =>
                    (e.currentTarget.style.transform = "scale(0.98)")
                  }
                  onMouseUp={(e) => (e.currentTarget.style.transform = "")}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "";
                    e.currentTarget.style.background =
                      "linear-gradient(180deg, var(--gold-warm), var(--gold))";
                  }}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background =
                      "linear-gradient(180deg, var(--gold), var(--gold-deep))")
                  }
                  style={{
                    position: "relative",
                    zIndex: 1,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 14,
                    background:
                      "linear-gradient(180deg, var(--gold-warm), var(--gold))",
                    color: "#fff",
                    padding: "18px 32px 16px",
                    borderRadius: 999,
                    border: 0,
                    cursor: "pointer",
                    font: "600 19px/1 var(--font-sans)",
                    letterSpacing: "-0.01em",
                    boxShadow:
                      "0 6px 20px -4px rgba(138,106,31,0.42), 0 2px 4px rgba(94,70,30,0.18), inset 0 1px 0 rgba(255,255,255,0.25)",
                    transition:
                      "background var(--dur-1), transform var(--dur-1)",
                  }}
                >
                  <img
                    src="/brand/icons/pencil.svg"
                    width="20"
                    height="20"
                    alt=""
                    style={{ filter: "invert(1) brightness(1.8)" }}
                  />
                  오늘의 일기 쓰기
                  <img
                    src="/brand/icons/arrow-right.svg"
                    width="16"
                    height="16"
                    alt=""
                    style={{
                      filter: "invert(1) brightness(1.8)",
                      opacity: 0.9,
                    }}
                  />
                </button>
              ) : (
                <button
                  onClick={() => setSelectedDiaryDate(TODAY_ISO)}
                  onMouseEnter={(e) =>
                    (e.currentTarget.style.background = "var(--gold-mist)")
                  }
                  onMouseLeave={(e) =>
                    (e.currentTarget.style.background = "var(--paper-bone)")
                  }
                  style={{
                    position: "relative",
                    zIndex: 1,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 12,
                    background: "var(--paper-bone)",
                    color: "var(--ink-walnut)",
                    padding: "16px 26px 14px",
                    borderRadius: 999,
                    border: "1.5px solid var(--gold)",
                    cursor: "pointer",
                    font: "600 17px/1 var(--font-sans)",
                    transition: "background var(--dur-1)",
                  }}
                >
                  <img
                    src="/brand/icons/check.svg"
                    width="18"
                    height="18"
                    alt=""
                  />
                  오늘의 일기 보기
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right: character stage */}
        <ComboStage combo={combo} />
      </section>

      {/* Mini calendar */}
      <section>
        <MiniCalendar
          year={today.getFullYear()}
          month={today.getMonth() + 1}
          todayISO={TODAY_ISO}
          savedDates={savedDates}
          view={calendarView}
          onDateClick={handleDateClick}
        />
      </section>

      {/* Footnote */}
      <div
        style={{
          font: "400 11px/1.4 var(--font-sans)",
          color: "var(--ink-stone)",
          textAlign: "center",
          padding: "8px 0 0",
          animation: "days-fade-in 400ms var(--ease-out) 700ms both",
        }}
      >
        매일 5가지 질문 · AI가 정리한 일기 · 잠들기 전 3분
      </div>

      <DiaryDetailModal
        date={selectedDiaryDate}
        onClose={() => setSelectedDiaryDate(null)}
        onUpdated={handleDiaryUpdated}
      />
      <ChatSessionModal
        date={selectedNewDate}
        onClose={() => setSelectedNewDate(null)}
        onComplete={handleChatComplete}
      />
    </div>
  );
}
