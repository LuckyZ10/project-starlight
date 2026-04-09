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
        <button onClick={() => router.back()} className="pixel-btn text-sm px-3 py-1">← Back</button>
        <h1 className="text-xl md:text-2xl font-bold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          📊 Learning Stats
        </h1>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8">
        <StatCard icon="⭐" label="Completed" value={`${stats.completed_nodes}`} sub={`of ${stats.total_nodes} nodes`} />
        <StatCard icon="🎯" label="Accuracy" value={`${stats.accuracy}%`} sub={`${stats.correct_answers}/${stats.total_answers} correct`} />
        <StatCard icon="💬" label="Messages" value={`${stats.total_messages}`} sub="chat messages" />
        <StatCard icon="📅" label="Active Days" value={`${stats.active_days}`} sub="days studied" />
      </div>

      {/* Progress Bar */}
      <div className="pixel-card p-5 mb-6">
        <h2 className="font-bold text-sm mb-3" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Overall Progress</h2>
        <div className="flex justify-between text-xs text-[var(--text-muted)] mb-1">
          <span>{stats.completed_nodes} completed · {stats.in_progress_nodes} in progress</span>
          <span>{completionPct}%</span>
        </div>
        <div className="h-4 bg-[var(--bg-primary)] rounded-full overflow-hidden border-2 border-[var(--border)]">
          <div
            className="h-full bg-[var(--accent-light)] transition-all rounded-full"
            style={{ width: `${completionPct}%` }}
          />
        </div>
        {stats.avg_score > 0 && (
          <p className="text-xs text-[var(--text-muted)] mt-2">Average score: {stats.avg_score}/100</p>
        )}
      </div>

      {/* Per-Cartridge Breakdown */}
      {stats.cartridges.length > 0 && (
        <div className="pixel-card p-5 mb-6">
          <h2 className="font-bold text-sm mb-4" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Cartridge Progress</h2>
          <div className="space-y-3">
            {stats.cartridges.map((c) => {
              const pct = c.total > 0 ? Math.round((c.completed / c.total) * 100) : 0;
              return (
                <div key={c.cartridge_id}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{c.cartridge_id}</span>
                    <span className="text-[var(--text-muted)]">{c.completed}/{c.total} ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
                    <div className="h-full bg-[var(--accent)] rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Stats Summary */}
      <div className="pixel-card p-5">
        <h2 className="font-bold text-sm mb-3" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Summary</h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Nodes mastered</span><span className="font-bold">{stats.completed_nodes}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Currently learning</span><span className="font-bold">{stats.in_progress_nodes}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Avg score</span><span className="font-bold">{stats.avg_score}</span></div>
          <div className="flex justify-between"><span className="text-[var(--text-muted)]">Accuracy</span><span className="font-bold">{stats.accuracy}%</span></div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub }: { icon: string; label: string; value: string; sub: string }) {
  return (
    <div className="pixel-card p-4 text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-xl font-bold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{value}</div>
      <div className="text-xs text-[var(--text-muted)]">{label}</div>
      <div className="text-xs text-[var(--text-muted)] mt-1">{sub}</div>
    </div>
  );
}
