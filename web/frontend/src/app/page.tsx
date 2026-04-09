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
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b-2 border-[var(--border)] px-6 py-4 bg-white">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[var(--accent)] flex items-center justify-center text-white font-bold text-lg pixel-border" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
              S
            </div>
            <span className="text-xl font-bold" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Starlight</span>
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <Link href="/stats" className="pixel-btn text-sm">📊 Stats</Link>
                <span className="text-sm text-[var(--text-secondary)]">{user.email}</span>
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
      <section className="max-w-6xl mx-auto px-6 py-16 text-center">
        <h1 className="text-4xl font-bold mb-4">
          Learn with <span className="text-[var(--accent)]">Starlight</span>
        </h1>
        <p className="text-[var(--text-secondary)] text-lg max-w-xl mx-auto">
          Choose a learning cartridge and master topics through interactive conversations with AI
        </p>
      </section>

      {/* Cartridge Grid */}
      <section className="max-w-6xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <CartridgeSkeleton key={i} />)
          ) : cartridges.map((c) => (
            <Link key={c.id} href={`/learn/${c.id}`} className="pixel-card p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-2xl">🎮</span>
                <h2 className="font-bold text-lg" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{c.title}</h2>
              </div>
              <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                <span>📖 {c.node_count} nodes</span>
                <span>v{c.version}</span>
              </div>
              <div className="mt-4 pixel-btn text-sm text-center block">Start Learning →</div>
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
