"use client";
import { useEffect, useState, useCallback } from "react";

export interface ToastMessage {
  id: string;
  type: "error" | "success" | "warning" | "info";
  text: string;
  duration?: number;
}

let addToastFn: ((t: Omit<ToastMessage, "id">) => void) | null = null;

/** Call from anywhere to show a toast */
export function showToast(type: ToastMessage["type"], text: string, duration = 5000) {
  addToastFn?.({ type, text, duration });
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((t: Omit<ToastMessage, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, t.duration || 5000);
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => { addToastFn = null; };
  }, [addToast]);

  const dismiss = (id: string) => setToasts((prev) => prev.filter((x) => x.id !== id));

  if (toasts.length === 0) return null;

  const colors: Record<string, string> = {
    error: "bg-red-600 text-white",
    success: "bg-green-600 text-white",
    warning: "bg-yellow-500 text-black",
    info: "bg-blue-600 text-white",
  };
  const icons: Record<string, string> = { error: "✕", success: "✓", warning: "⚠", info: "ℹ" };

  return (
    <div className="fixed bottom-4 right-4 z-[100] space-y-2 max-w-sm">
      {toasts.map((t) => (
        <div key={t.id} className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg animate-slide ${colors[t.type]}`}>
          <span className="text-lg">{icons[t.type]}</span>
          <span className="text-sm flex-1">{t.text}</span>
          <button onClick={() => dismiss(t.id)} className="opacity-70 hover:opacity-100 text-lg">×</button>
        </div>
      ))}
    </div>
  );
}
