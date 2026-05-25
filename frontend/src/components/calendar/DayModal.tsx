import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../../api/client";
import { DiaryModalContent } from "./DiaryModalContent";

interface DayModalProps {
  date: string;
  onClose: () => void;
}

type Mode = "loading" | "diary" | "error";

interface DiaryState {
  body: string;
  emotion?: string;
}

export function DayModal({ date, onClose }: DayModalProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("loading");
  const [diary, setDiary] = useState<DiaryState | null>(null);

  useEffect(() => {
    client
      .get(`/diary/${date}`)
      .then((res) => {
        if (!res.data.body) {
          navigate(`/qna/${date}`, { replace: true });
        } else {
          setDiary({ body: res.data.body, emotion: res.data.emotion });
          setMode("diary");
        }
      })
      .catch((e) => {
        const status = (e as { response?: { status?: number } }).response
          ?.status;
        if (status === 404) {
          navigate(`/qna/${date}`, { replace: true });
        } else setMode("error");
      });
  }, [date, navigate, onClose]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${date} 일기`}
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
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
          maxWidth: 440,
          maxHeight: "85vh",
          overflowY: "auto",
          padding: 24,
          position: "relative",
          boxShadow: "var(--shadow-3)",
          animation: "days-rise 280ms var(--ease-out) 60ms both",
        }}
      >
        <button
          type="button"
          aria-label="닫기"
          onClick={onClose}
          style={{
            position: "absolute",
            top: 12,
            right: 12,
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

        {mode === "loading" && (
          <div
            style={{
              padding: "48px 0",
              textAlign: "center",
              color: "var(--ink-hint)",
              fontFamily: "var(--font-sans)",
            }}
          >
            불러오는 중...
          </div>
        )}

        {mode === "diary" && diary && (
          <DiaryModalContent
            date={date}
            body={diary.body}
            emotion={diary.emotion}
          />
        )}

        {mode === "error" && (
          <div
            style={{
              padding: "48px 0",
              textAlign: "center",
              color: "var(--accent-clay)",
              fontFamily: "var(--font-sans)",
            }}
          >
            불러오지 못했어요.
          </div>
        )}
      </div>
    </div>
  );
}
