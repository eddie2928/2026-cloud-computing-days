import { useEffect, useState } from "react";
import { useAuth, apiHeaders } from "../components/AuthProvider";

export function PromptEditor() {
  const { token } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    fetch("/api/audit?limit=1", { headers: apiHeaders(token) });
    // Load current prompt from settings
    fetch("/api/settings/prompt-get", { headers: apiHeaders(token) })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d?.system_prompt) setPrompt(d.system_prompt); })
      .catch(() => {});
  }, [token]);

  async function save() {
    setStatus("Saving...");
    const res = await fetch("/api/settings/prompt", {
      method: "PUT",
      headers: apiHeaders(token),
      body: JSON.stringify({ system_prompt: prompt }),
    });
    setStatus(res.ok ? "Saved." : "Error saving.");
    setTimeout(() => setStatus(""), 3000);
  }

  return (
    <div>
      <h2>Bedrock System Prompt Editor</h2>
      <p style={{ color: "#666" }}>Edit the security inspection prompt used by Bedrock Agent.</p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={18}
        style={{ width: "100%", fontFamily: "monospace", fontSize: 13, padding: "0.5rem", boxSizing: "border-box" }}
        data-testid="prompt-textarea"
      />
      <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "1rem" }}>
        <button onClick={save} style={btnStyle} data-testid="save-prompt-btn">Save Prompt</button>
        {status && <span style={{ color: status.includes("Error") ? "red" : "green" }}>{status}</span>}
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  background: "#e94560", color: "#fff", border: "none", padding: "0.5rem 1.2rem",
  cursor: "pointer", borderRadius: 4,
};
