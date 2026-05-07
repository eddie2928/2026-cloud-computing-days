import { useEffect, useRef, useState } from "react";
import { useAuth } from "../components/AuthProvider";

interface Event {
  event_id: string;
  ts: string;
  user_id: string;
  verdict: string;
  reasons_json?: string;
  latency_ms?: number;
}

export function PipelineStream() {
  const { token } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/pipeline/stream`);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const evt: Event = JSON.parse(msg.data);
        setEvents((prev) => [evt, ...prev].slice(0, 200));
      } catch {}
    };

    return () => ws.close();
  }, []);

  return (
    <div>
      <h2>Pipeline Stream</h2>
      <p style={{ color: "#666" }}>Real-time events via WebSocket</p>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#1a1a2e", color: "#fff" }}>
            <th style={th}>Time</th>
            <th style={th}>User</th>
            <th style={th}>Verdict</th>
            <th style={th}>Latency</th>
            <th style={th}>Reasons</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.event_id} style={{ background: e.verdict === "BLOCK" ? "#fff0f0" : "#f0fff0" }}>
              <td style={td}>{new Date(e.ts).toLocaleTimeString()}</td>
              <td style={td}>{e.user_id}</td>
              <td style={{ ...td, fontWeight: "bold", color: e.verdict === "BLOCK" ? "#e94560" : "#2e7d32" }}>{e.verdict}</td>
              <td style={td}>{e.latency_ms ? `${e.latency_ms}ms` : "-"}</td>
              <td style={td}>{e.reasons_json ? JSON.parse(e.reasons_json).join(", ") : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {events.length === 0 && <p style={{ color: "#999", textAlign: "center", marginTop: "2rem" }}>Waiting for events...</p>}
    </div>
  );
}

const th: React.CSSProperties = { padding: "0.5rem", textAlign: "left", border: "1px solid #333" };
const td: React.CSSProperties = { padding: "0.4rem 0.5rem", border: "1px solid #ddd" };
