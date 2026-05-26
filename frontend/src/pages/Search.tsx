import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { searchDiaries, type DiarySearchItem } from "../lib/search";
import { Header } from "../components/layout/Header";
import { PillInput } from "../components/days/PillInput";
import { Icon } from "../components/days/Icon";

export function Search() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [results, setResults] = useState<DiarySearchItem[]>([]);

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
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Header title="검색" showBack />

      <div style={{ padding: "0 16px", display: "flex", flexDirection: "column", gap: 12 }}>
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
              onClick={() => navigate(`/diary/${item.date}`)}
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
