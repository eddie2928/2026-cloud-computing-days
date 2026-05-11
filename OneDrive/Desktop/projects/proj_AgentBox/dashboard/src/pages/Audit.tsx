import { useState } from "react";
import { useAuth, apiHeaders } from "../components/AuthProvider";

interface AuditRow {
  event_id: string;
  ts: string;
  user_id: string;
  verdict: string;
  reasons_json?: string;
  latency_ms?: number;
  prompt_hash?: string;
}

export function Audit() {
  const { token } = useAuth();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [verdict, setVerdict] = useState("");
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);

  async function query() {
    setLoading(true);
    const params = new URLSearchParams({ limit: "100" });
    if (from) params.set("from_ts", from);
    if (to) params.set("to_ts", to);
    if (verdict) params.set("verdict", verdict);
    const res = await fetch(`/api/audit?${params}`, { headers: apiHeaders(token) });
    if (res.ok) setRows(await res.json());
    setLoading(false);
  }

  function exportCSV() {
    const headers = ["event_id", "ts", "user_id", "verdict", "latency_ms", "reasons"];
    const csvRows = rows.map((r) =>
      [r.event_id, r.ts, r.user_id, r.verdict, r.latency_ms ?? "",
       r.reasons_json ? JSON.parse(r.reasons_json).join("|") : ""].join(",")
    );
    const blob = new Blob([[headers.join(","), ...csvRows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    Object.assign(document.createElement("a"), { href: url, download: "audit.csv" }).click();
  }

  return (
    <div>
      <h2>Audit Log</h2>
      <p style={{ color: "#666", fontSize: 13, marginTop: 0, marginBottom: "1rem", lineHeight: 1.5 }}>
        DynamoDB 에 영구 저장된 ALLOW/BLOCK 판정 이력입니다. 페이지 진입 시 최근 100건을 자동 조회하고,
        3초마다 새 이벤트를 상단에 추가합니다. 우상단 Pause 버튼으로 폴링을 일시 중지할 수 있습니다.
        From/To/Verdict 로 과거 구간을 검색하거나 CSV 로 내보낼 수 있습니다.
      </p>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <label>From: <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
        <label>To: <input type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} /></label>
        <label>
          Verdict:{" "}
          <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
            <option value="">All</option>
            <option value="ALLOW">ALLOW</option>
            <option value="BLOCK">BLOCK</option>
          </select>
        </label>
        <button onClick={query} style={btnStyle} data-testid="audit-query-btn">Query</button>
        {rows.length > 0 && (
          <button onClick={exportCSV} style={{ ...btnStyle, background: "#2e7d32" }} data-testid="audit-export-btn">
            Export CSV
          </button>
        )}
      </div>
      {loading && <p>Loading...</p>}
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ background: "#1a1a2e", color: "#fff" }}>
            {["Time", "User", "Verdict", "Latency", "Reasons", "Prompt Hash"].map((h) => (
              <th key={h} style={th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.event_id} style={{ background: r.verdict === "BLOCK" ? "#fff0f0" : "#fff" }}>
              <td style={td}>{new Date(r.ts).toLocaleString()}</td>
              <td style={td}>{r.user_id}</td>
              <td style={{ ...td, color: r.verdict === "BLOCK" ? "#e94560" : "#2e7d32", fontWeight: "bold" }}>{r.verdict}</td>
              <td style={td}>{r.latency_ms ? `${r.latency_ms}ms` : "-"}</td>
              <td style={td}>{r.reasons_json ? JSON.parse(r.reasons_json).join("; ") : ""}</td>
              <td style={{ ...td, fontFamily: "monospace", fontSize: 11 }}>{(r.prompt_hash ?? "").slice(0, 12)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && !loading && <p style={{ color: "#999", textAlign: "center", marginTop: "1rem" }}>No results.</p>}
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: "#e94560", color: "#fff", border: "none", padding: "0.4rem 1rem",
  cursor: "pointer", borderRadius: 4,
};
const th: React.CSSProperties = { padding: "0.4rem", textAlign: "left", border: "1px solid #333" };
const td: React.CSSProperties = { padding: "0.3rem 0.4rem", border: "1px solid #ddd" };
