"use client";
import { useEffect, useState, useCallback } from "react";

export interface ToastMessage {
  id: string;
  type: "error" | "success" | "warning" | "info";
  text: string;
  duration?: number;
}

let addToastFn: ((t: Omit<ToastMessage, "id">) => void) | null = null;

export function showToast(type: ToastMessage["type"], text: string, duration = 5000) {
  addToastFn?.({ type, text, duration });
}

function CheckIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>; }
function XCircleIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>; }
function AlertIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>; }
function InfoIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>; }
function CloseIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>; }

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

  const styles: Record<string, { bg: string; border: string; icon: React.ReactNode }> = {
    error: { bg: "bg-[var(--error)]/5", border: "border-[var(--error)]/20", icon: <XCircleIcon /> },
    success: { bg: "bg-[var(--success)]/5", border: "border-[var(--success)]/20", icon: <CheckIcon /> },
    warning: { bg: "bg-[var(--warning)]/5", border: "border-[var(--warning)]/20", icon: <AlertIcon /> },
    info: { bg: "bg-blue-500/5", border: "border-blue-500/20", icon: <InfoIcon /> },
  };

  return (
    <div className="fixed bottom-4 right-4 z-[100] space-y-2 max-w-sm">
      {toasts.map((t) => {
        const s = styles[t.type];
        return (
          <div key={t.id} className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg animate-slide ${s.bg} ${s.border}`}>
            <span className="text-[var(--text-secondary)] shrink-0">{s.icon}</span>
            <span className="text-sm flex-1">{t.text}</span>
            <button onClick={() => dismiss(t.id)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] shrink-0">
              <CloseIcon />
            </button>
          </div>
        );
      })}
    </div>
  );
}
