import { Outlet, NavLink } from "react-router-dom";
import { useAuth } from "./AuthProvider";

const links = [
  { to: "/pipeline", label: "Pipeline" },
  { to: "/prompt", label: "Prompt Editor" },
  { to: "/kb", label: "KB Settings" },
  { to: "/audit", label: "Audit" },
];

export function Layout() {
  const { setToken } = useAuth();

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui" }}>
      <nav style={{ width: 200, background: "#1a1a2e", padding: "1rem", color: "#eee" }}>
        <h2 style={{ color: "#e94560", marginTop: 0 }}>AgentBox</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {links.map((l) => (
            <li key={l.to} style={{ margin: "0.5rem 0" }}>
              <NavLink
                to={l.to}
                style={({ isActive }) => ({
                  color: isActive ? "#e94560" : "#ccc",
                  textDecoration: "none",
                })}
              >
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <button
          onClick={() => setToken("")}
          style={{ marginTop: "auto", background: "none", border: "1px solid #555", color: "#ccc", cursor: "pointer", padding: "0.3rem 0.6rem" }}
        >
          Logout
        </button>
      </nav>
      <main style={{ flex: 1, padding: "1.5rem", background: "#f5f5f5" }}>
        <Outlet />
      </main>
    </div>
  );
}
