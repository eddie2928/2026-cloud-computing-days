import { createContext, useContext, useState, ReactNode } from "react";

interface AuthCtx {
  token: string;
  setToken: (t: string) => void;
}

const Ctx = createContext<AuthCtx>({ token: "", setToken: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState(() => localStorage.getItem("admin_token") ?? "");

  function setToken(t: string) {
    localStorage.setItem("admin_token", t);
    setTokenState(t);
  }

  return <Ctx.Provider value={{ token, setToken }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export function apiHeaders(token: string): HeadersInit {
  return { "X-Admin-Token": token, "Content-Type": "application/json" };
}
