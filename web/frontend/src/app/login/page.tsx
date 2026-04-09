"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const [email, setEmail] = useState("demo@starlight.ai");
  const [password, setPassword] = useState("123456");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [debug, setDebug] = useState("");
  const { setAuth } = useAuthStore();

  const handleLogin = async () => {
    setError("");
    setLoading(true);
    setDebug("Sending request...");
    try {
      setDebug(`Calling API: login(${email}, ***)`);
      const res = await api.login(email, password);
      setDebug(`Got response: token=${res.token ? res.token.substring(0,20) + "..." : "null"}, user=${JSON.stringify(res.email)}`);
      setAuth(res.token, { id: res.id, email: res.email });
      setDebug("Token saved, redirecting...");
      window.location.href = "/";
    } catch (err: any) {
      setDebug(`Error: ${err?.message || err}`);
      setError(err?.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="pixel-card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center" style={{ fontFamily: "'JetBrains Mono', monospace" }}>🔐 Login</h1>
        {error && <div className="mb-4 p-3 bg-red-50 border-2 border-red-400 rounded text-sm">{error}</div>}
        {debug && <div className="mb-4 p-3 bg-green-50 border-2 border-green-400 rounded text-xs font-mono break-all">{debug}</div>}
        <div className="space-y-4">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
            className="w-full p-3 border-2 border-[var(--border)] rounded text-sm focus:border-[var(--accent-light)] focus:outline-none" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password"
            className="w-full p-3 border-2 border-[var(--border)] rounded text-sm focus:border-[var(--accent-light)] focus:outline-none" />
          <button onClick={handleLogin} disabled={loading} className="pixel-btn pixel-btn-primary w-full">
            {loading ? "⏳ Logging in..." : "Login"}
          </button>
        </div>
        <p className="mt-4 text-center text-sm text-[var(--text-secondary)]">
          No account? <a href="/register" className="text-[var(--accent)] underline">Register</a>
        </p>
      </div>
    </div>
  );
}
