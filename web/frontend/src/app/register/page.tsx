"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

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
    <div className="min-h-screen flex items-center justify-center">
      <div className="pixel-card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center" style={{ fontFamily: "'JetBrains Mono', monospace" }}>🎮 Register</h1>
        {error && <div className="mb-4 p-3 bg-red-50 border-2 border-[var(--error)] rounded text-sm">{error}</div>}
        <form onSubmit={handleRegister} className="space-y-4">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required
            className="w-full p-3 border-2 border-[var(--border)] rounded text-sm focus:border-[var(--accent-light)] focus:outline-none" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (6+ chars)" required
            className="w-full p-3 border-2 border-[var(--border)] rounded text-sm focus:border-[var(--accent-light)] focus:outline-none" />
          <button type="submit" className="pixel-btn pixel-btn-primary w-full">Register</button>
        </form>
        <p className="mt-4 text-center text-sm text-[var(--text-secondary)]">
          Already have an account? <a href="/login" className="text-[var(--accent)] underline">Login</a>
        </p>
      </div>
    </div>
  );
}
