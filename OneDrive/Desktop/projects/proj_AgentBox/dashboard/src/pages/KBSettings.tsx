import { useEffect, useState } from "react";
import { useAuth, apiHeaders } from "../components/AuthProvider";

export function KBSettings() {
  const { token } = useAuth();
  const [ttl, setTtl] = useState(5);
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/api/settings/kb-ttl-get", { headers: apiHeaders(token) })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d?.ttl_minutes) setTtl(d.ttl_minutes); })
      .catch(() => {});
  }, [token]);

  async function save() {
    setStatus("Saving...");
    const res = await fetch("/api/settings/kb-ttl", {
      method: "PUT",
      headers: apiHeaders(token),
      body: JSON.stringify({ ttl_minutes: ttl }),
    });
    setStatus(res.ok ? "Saved." : "Error saving.");
    setTimeout(() => setStatus(""), 3000);
  }

  return (
    <div>
      <h2>KB Staging Bucket Settings</h2>
      <p style={{ color: "#666" }}>Set how long decrypted code stays in the KB staging bucket before deletion.</p>
      <label style={{ display: "block", marginBottom: "0.5rem" }}>
        TTL (minutes): 1–60
      </label>
      <input
        type="number"
        min={1}
        max={60}
        value={ttl}
        onChange={(e) => setTtl(Number(e.target.value))}
        style={{ padding: "0.4rem", width: 80, marginRight: "1rem" }}
        data-testid="kb-ttl-input"
      />
      <button onClick={save} style={btnStyle} data-testid="save-kb-btn">Save</button>
      {status && <span style={{ marginLeft: "1rem", color: status.includes("Error") ? "red" : "green" }}>{status}</span>}
      <p style={{ marginTop: "1.5rem", fontSize: 13, color: "#888" }}>
        Zero-Knowledge guarantee: decrypted code is automatically purged after {ttl} minute(s) or sooner upon inspection completion.
      </p>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: "#1a1a2e", color: "#fff", border: "none", padding: "0.4rem 1rem",
  cursor: "pointer", borderRadius: 4,
};
