import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./components/AuthProvider";
import { Login } from "./pages/Login";
import { Layout } from "./components/Layout";
import { PipelineStream } from "./pages/PipelineStream";
import { PromptEditor } from "./pages/PromptEditor";
import { KBSettings } from "./pages/KBSettings";
import { Audit } from "./pages/Audit";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<PrivateLayout />}>
            <Route path="/" element={<Navigate to="/pipeline" replace />} />
            <Route path="/pipeline" element={<PipelineStream />} />
            <Route path="/prompt" element={<PromptEditor />} />
            <Route path="/kb" element={<KBSettings />} />
            <Route path="/audit" element={<Audit />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

function PrivateLayout() {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <Layout />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
