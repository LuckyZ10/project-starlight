"use client";
import { useEffect, useState } from "react";

interface Toast {
  id: number;
  message: string;
  type: "success" | "error" | "info";
}

let toastId = 0;
const listeners: Set<(t: Toast) => void> = new Set();

export function showToast(message: string, type: Toast["type"] = "info") {
  const t: Toast = { id: ++toastId, message, type };
  listeners.forEach((fn) => fn(t));
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const handler = (t: Toast) => {
      setToasts((prev) => [...prev, t]);
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== t.id)), 4000);
    };
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((t) => (
        <div key={t.id} className={`animate-slide px-4 py-3 rounded shadow-lg text-sm font-medium max-w-sm ${
          t.type === "error" ? "bg-[var(--error)] text-white" :
          t.type === "success" ? "bg-[var(--success)] text-white" :
          "bg-white border-2 border-[var(--border)] text-[var(--text-primary)]"
        }`}>
          {t.type === "error" ? "❌ " : t.type === "success" ? "✅ " : "ℹ️ "}{t.message}
        </div>
      ))}
    </div>
  );
}
