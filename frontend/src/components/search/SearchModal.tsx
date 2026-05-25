import { useEffect, useState } from "react";
import { searchDiaries, type DiarySearchItem } from "../../lib/search";
import { PillInput } from "../days/PillInput";
import { Icon } from "../days/Icon";

interface SearchModalProps {
  onClose: () => void;
  onSelect: (date: string) => void;
}

export function SearchModal({ onClose, onSelect }: SearchModalProps) {
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [results, setResults] = useState<DiarySearchItem[]>([]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    if (!debouncedQ.trim()) {
      setResults([]);
      return;
    }
    searchDiaries(debouncedQ)
      .then(setResults)
      .catch(() => setResults([]));
  }, [debouncedQ]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="일기 검색"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "15vh",
        zIndex: 1000,
        animation: "days-fade-in 200ms var(--ease-out) both",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--paper-pure)",
          borderRadius: 20,
          width: "92%",
          maxWidth: 420,
          maxHeight: "70vh",
          overflowY: "auto",
          padding: 20,
          boxShadow: "var(--shadow-3)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          animation: "days-rise 260ms var(--ease-out) 40ms both",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 700,
              fontSize: "var(--t-md)",
              color: "var(--sage-ink)",
            }}
          >
            검색
          </span>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              color: "var(--ink-meta)",
              lineHeight: 1,
              padding: "4px 8px",
            }}
          >
            ×
          </button>
        </div>

        <PillInput
          value={q}
          onChange={setQ}
          placeholder="내용으로 검색"
          ariaLabel="일기 검색 입력"
          icon={<Icon name="book" size={16} />}
        />

        {debouncedQ && results.length === 0 && (
          <p
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--t-sm)",
              color: "var(--ink-hint)",
              textAlign: "center",
              padding: "8px 0",
            }}
          >
            결과가 없어요
          </p>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {results.map((item) => (
            <button
              key={item.date}
              type="button"
              onClick={() => onSelect(item.date)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: 4,
                padding: "10px 14px",
                background: "var(--paper-bone)",
                border: "1px solid var(--line-faint)",
                borderRadius: "var(--r-3)",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                color: "var(--ink-body)",
                textAlign: "left",
              }}
            >
              <span
                style={{
                  fontSize: "var(--t-sm)",
                  color: "var(--ink-meta)",
                  fontWeight: 600,
                }}
              >
                {item.date}
              </span>
              <span style={{ fontSize: "var(--t-base)" }}>{item.snippet}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
