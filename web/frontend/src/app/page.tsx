"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { CartridgeSkeleton } from "@/components/Skeleton";
import { showToast } from "@/components/Toast";

interface Cartridge {
  id: string;
  title: string;
  version: string;
  node_count: number;
}

export default function LandingPage() {
  const [loading, setLoading] = useState(true);
  const [cartridges, setCartridges] = useState<Cartridge[]>([]);
  const { user } = useAuthStore();

  useEffect(() => {
    api.listCartridges()
      .then(setCartridges)
      .catch(() => showToast("error", "Failed to load cartridges"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <header className="border-b-2 border-[var(--border)] bg-white sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-[var(--accent)] flex items-center justify-center text-white font-bold text-base" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              S
            </div>
            <span className="text-lg font-bold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Starlight</span>
          </div>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Link href="/stats" className="pixel-btn text-sm">📊 Stats</Link>
                <span className="text-sm text-[var(--text-secondary)] hidden sm:inline">{user.email}</span>
              </>
            ) : (
              <>
                <Link href="/login" className="pixel-btn text-sm">Login</Link>
                <Link href="/register" className="pixel-btn pixel-btn-primary text-sm">Register</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 md:px-6 py-12 md:py-20 text-center">
        <h1 className="text-3xl md:text-4xl font-bold mb-4">
          Learn with <span className="text-[var(--accent)]">Starlight</span>
        </h1>
        <p className="text-[var(--text-secondary)] text-base md:text-lg max-w-lg mx-auto leading-relaxed">
          Master topics through interactive conversations with AI
        </p>
      </section>

      {/* Grid */}
      <section className="max-w-5xl mx-auto px-4 md:px-6 pb-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <CartridgeSkeleton key={i} />)
          ) : cartridges.map((c) => (
            <Link key={c.id} href={`/learn/${c.id}`}
              className="pixel-card p-5 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-2xl">🎮</span>
                <h2 className="font-bold text-base group-hover:text-[var(--accent)] transition-colors" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                  {c.title}
                </h2>
              </div>
              <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                <span>📖 {c.node_count} nodes</span>
                <span>v{c.version}</span>
              </div>
              <div className="mt-4 text-center py-2 text-sm font-semibold text-[var(--accent)] group-hover:bg-[var(--accent)] group-hover:text-white rounded-lg border-2 border-[var(--border)] group-hover:border-[var(--accent)] transition-all">
                Start Learning →
              </div>
            </Link>
          ))}
          {!loading && cartridges.length === 0 && (
            <div className="col-span-full text-center text-[var(--text-muted)] py-12">
              No cartridges available. Run the factory first!
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
