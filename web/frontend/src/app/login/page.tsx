"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

function SparklesIcon() { return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/></svg>; }

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
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)] p-4">
      <div className="card p-8 w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white">
            <SparklesIcon />
          </div>
        </div>
        <h1 className="text-xl font-bold text-center mb-1">Welcome back</h1>
        <p className="text-sm text-[var(--text-secondary)] text-center mb-6">Sign in to continue learning</p>
        {error && <div className="mb-4 p-3 bg-[var(--error)]/5 border border-[var(--error)]/20 rounded-xl text-sm text-[var(--error)]">{error}</div>}
        {debug && <div className="mb-4 p-3 bg-[var(--bg-primary)] border border-[var(--border)] rounded-xl text-xs font-mono break-all text-[var(--text-muted)]">{debug}</div>}
        <div className="space-y-3">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email"
            className="input" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password"
            className="input" />
          <button onClick={handleLogin} disabled={loading}
            className="btn btn-primary w-full">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </div>
        <p className="mt-5 text-center text-sm text-[var(--text-muted)]">
          No account? <a href="/register" className="text-[var(--accent)] hover:underline font-medium">Create one</a>
        </p>
      </div>
    </div>
  );
}
