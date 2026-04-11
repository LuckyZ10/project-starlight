"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface Stats {
  total_nodes: number;
  completed_nodes: number;
  in_progress_nodes: number;
  avg_score: number;
  total_answers: number;
  correct_answers: number;
  accuracy: number;
  total_messages: number;
  active_days: number;
  cartridges: { cartridge_id: string; total: number; completed: number }[];
}

function ChevronLeftIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>; }
function CheckCircleIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>; }
function TargetIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>; }
function MessageCircleIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>; }
function CalendarIcon() { return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>; }

export default function StatsPage() {
  const router = useRouter();
  const { token } = useAuthStore();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    api.getStats().then(setStats).catch(console.error).finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-[var(--text-muted)]">Loading...</div>;
  if (!stats) return <div className="min-h-screen flex items-center justify-center text-[var(--text-muted)]">No data yet</div>;

  const completionPct = stats.total_nodes > 0 ? Math.round((stats.completed_nodes / stats.total_nodes) * 100) : 0;

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] p-4 md:p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <button onClick={() => router.back()} className="icon-btn"><ChevronLeftIcon /></button>
        <h1 className="text-xl font-bold">Learning Stats</h1>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard icon={<CheckCircleIcon />} label="Completed" value={`${stats.completed_nodes}`} sub={`of ${stats.total_nodes} nodes`} />
        <StatCard icon={<TargetIcon />} label="Accuracy" value={`${stats.accuracy}%`} sub={`${stats.correct_answers}/${stats.total_answers} correct`} />
        <StatCard icon={<MessageCircleIcon />} label="Messages" value={`${stats.total_messages}`} sub="chat messages" />
        <StatCard icon={<CalendarIcon />} label="Active Days" value={`${stats.active_days}`} sub="days studied" />
      </div>

      {/* Progress Bar */}
      <div className="card p-5 mb-4">
        <h2 className="font-semibold text-sm mb-3">Overall Progress</h2>
        <div className="flex justify-between text-xs text-[var(--text-muted)] mb-2">
          <span>{stats.completed_nodes} completed · {stats.in_progress_nodes} in progress</span>
          <span className="font-medium">{completionPct}%</span>
        </div>
        <div className="h-2 bg-[var(--border)] rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent-light)] rounded-full transition-all"
            style={{ width: `${completionPct}%` }}
          />
        </div>
        {stats.avg_score > 0 && (
          <p className="text-xs text-[var(--text-muted)] mt-2">Average score: {stats.avg_score}/100</p>
        )}
      </div>

      {/* Per-Cartridge Breakdown */}
      {stats.cartridges.length > 0 && (
        <div className="card p-5 mb-4">
          <h2 className="font-semibold text-sm mb-4">Cartridge Progress</h2>
          <div className="space-y-3">
            {stats.cartridges.map((c) => {
              const pct = c.total > 0 ? Math.round((c.completed / c.total) * 100) : 0;
              return (
                <div key={c.cartridge_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{c.cartridge_id}</span>
                    <span className="text-[var(--text-muted)] text-xs">{c.completed}/{c.total} ({pct}%)</span>
                  </div>
                  <div className="h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div className="h-full bg-[var(--accent)] rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="card p-5">
        <h2 className="font-semibold text-sm mb-3">Summary</h2>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Nodes mastered</span><span className="font-medium">{stats.completed_nodes}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Currently learning</span><span className="font-medium">{stats.in_progress_nodes}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Avg score</span><span className="font-medium">{stats.avg_score}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Accuracy</span><span className="font-medium">{stats.accuracy}%</span></div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub: string }) {
  return (
    <div className="card p-4">
      <div className="text-[var(--accent)] mb-2">{icon}</div>
      <div className="text-xl font-bold">{value}</div>
      <div className="text-xs text-[var(--text-muted)]">{label}</div>
      <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{sub}</div>
    </div>
  );
}
