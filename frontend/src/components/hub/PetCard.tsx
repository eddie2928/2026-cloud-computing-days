import { useState, useEffect } from "react";
import client from "../../api/client";

const PET_EMOJI: Record<number, string> = {
  1: "🥚",
  2: "🐣",
  3: "🐥",
  4: "🐤",
  5: "🐔",
};

interface PetData {
  level: number;
  xp: number;
  xp_to_next: number;
}

export function PetCard() {
  const [pet, setPet] = useState<PetData | null>(null);

  useEffect(() => {
    client
      .get("/pet")
      .then((res) => setPet(res.data))
      .catch(() => {});
  }, []);

  const emoji = pet ? (PET_EMOJI[Math.min(pet.level, 5)] ?? "🐔") : "🥚";
  const label = pet ? `레벨 ${pet.level}` : "다마고치가 곧 찾아와요";

  return (
    <div
      role="region"
      aria-label="다마고치"
      style={{
        borderRadius: "var(--r-5)",
        border: "2px solid var(--sage-mist)",
        background: "rgba(255,255,255,0.4)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: 16,
        color: "var(--ink-meta)",
        font: "500 14px/1.4 var(--font-sans)",
      }}
    >
      <span
        style={{
          fontSize: 40,
          display: "inline-block",
          animation: "home-float 4s ease-in-out infinite",
        }}
        aria-hidden
      >
        {emoji}
      </span>
      <div
        style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}
      >
        <span style={{ color: "var(--sage-ink)", fontWeight: 600 }}>
          {label}
        </span>
        {pet && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12 }}>XP</span>
              <div
                style={{
                  flex: 1,
                  height: 6,
                  background: "var(--sage-wash)",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${(pet.xp / pet.xp_to_next) * 100}%`,
                    background: "var(--sage-leaf)",
                    borderRadius: 3,
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
              <span style={{ fontSize: 12 }}>
                {pet.xp}/{pet.xp_to_next}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
