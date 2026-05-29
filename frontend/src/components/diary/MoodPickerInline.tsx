import { useState } from "react";
import client from "../../api/client";
import { MoodEmoji, type Mood, MOOD_EMOJI } from "../days/MoodEmoji";

const MOODS: Mood[] = ["happy", "sad", "angry", "neutral", "bored"];

interface MoodPickerInlineProps {
  date: string;
  initial?: Mood;
}

export function MoodPickerInline({ date, initial }: MoodPickerInlineProps) {
  const [selected, setSelected] = useState<Mood | undefined>(initial);
  const [pending, setPending] = useState(false);

  const pick = async (mood: Mood) => {
    const prev = selected;
    setSelected(mood);
    setPending(true);
    try {
      await client.patch(`/diary/${date}/emotion`, { emotion: mood });
    } catch {
      setSelected(prev);
    } finally {
      setPending(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-around",
        padding: "12px 0",
        opacity: pending ? 0.7 : 1,
        transition: "opacity var(--dur-1)",
      }}
    >
      {MOODS.map((mood) => (
        <button
          key={mood}
          aria-label={mood}
          aria-pressed={selected === mood}
          onClick={() => pick(mood)}
          style={
            {
              border: "none",
              cursor: "pointer",
              padding: "8px",
              borderRadius: "var(--r-pill)",
              background:
                selected === mood ? "var(--sage-wash)" : "transparent",
              transform: selected === mood ? "scale(1.2)" : "scale(1)",
              animation:
                selected === mood
                  ? "days-mood-bounce 280ms var(--ease-soft) both"
                  : "none",
              transition:
                "transform var(--dur-2) var(--ease-soft), background var(--dur-1)",
            } as React.CSSProperties
          }
        >
          <MoodEmoji mood={mood} size={32} float />
        </button>
      ))}
    </div>
  );
}

export { MOOD_EMOJI };
