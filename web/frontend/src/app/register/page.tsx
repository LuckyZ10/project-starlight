"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

function SparklesIcon() { return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/></svg>; }

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { setAuth } = useAuthStore();
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { setError("Password must be at least 6 characters"); return; }
    try {
      const res = await api.register(email, password);
      setAuth(res.token, { id: res.id, email: res.email });
      router.push("/");
    } catch (err) {
      setError(String(err));
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
        <h1 className="text-xl font-bold text-center mb-1">Create account</h1>
        <p className="text-sm text-[var(--text-secondary)] text-center mb-6">Start your learning journey</p>
        {error && <div className="mb-4 p-3 bg-[var(--error)]/5 border border-[var(--error)]/20 rounded-xl text-sm text-[var(--error)]">{error}</div>}
        <form onSubmit={handleRegister} className="space-y-3">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required
            className="input" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (6+ chars)" required
            className="input" />
          <button type="submit" className="btn btn-primary w-full">Create account</button>
        </form>
        <p className="mt-5 text-center text-sm text-[var(--text-muted)]">
          Already have an account? <a href="/login" className="text-[var(--accent)] hover:underline font-medium">Sign in</a>
        </p>
      </div>
    </div>
  );
}
