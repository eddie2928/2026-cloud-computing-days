import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../components/AuthProvider";

export function Login() {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const { setToken } = useAuth();
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/audit?limit=1", {
      headers: { "X-Admin-Token": value },
    });
    if (res.ok || res.status === 200) {
      setToken(value);
      nav("/pipeline");
    } else {
      setError("Invalid token");
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "#1a1a2e" }}>
      <form onSubmit={submit} style={{ background: "#fff", padding: "2rem", borderRadius: 8, minWidth: 300 }}>
        <h2 style={{ marginTop: 0 }}>AgentBox Login</h2>
        <input
          type="password"
          placeholder="Admin Token"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          style={{ width: "100%", padding: "0.5rem", marginBottom: "1rem", boxSizing: "border-box" }}
          data-testid="token-input"
        />
        {error && <p style={{ color: "red" }}>{error}</p>}
        <button type="submit" style={{ width: "100%", padding: "0.5rem", background: "#e94560", color: "#fff", border: "none", cursor: "pointer", borderRadius: 4 }}>
          Login
        </button>
      </form>
    </div>
  );
}
