"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { CartridgeSkeleton } from "@/components/Skeleton";
import { showToast } from "@/components/Toast";
import { useTheme } from "@/components/ThemeToggle";

interface Cartridge {
  id: string;
  title: string;
  version: string;
  node_count: number;
}

/* ─── SVG Icons ─── */
function LogoIcon({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none">
      <rect x="2" y="2" width="28" height="28" rx="8" fill="var(--accent)" />
      <path d="M10 16l4 4 8-8" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function BookIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>;
}

function LayersIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>;
}

function ArrowRightIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>;
}

function ChartIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>;
}

function TopicIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>;
}

function SunIcon() { return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>; }
function MoonIcon() { return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>; }
function LogOutIcon() {
  return <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>;
}

export default function LandingPage() {
  const [loading, setLoading] = useState(true);
  const [cartridges, setCartridges] = useState<Cartridge[]>([]);
  const { user, logout } = useAuthStore();
  const { dark, toggle: toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api.listCartridges()
      .then(setCartridges)
      .catch(() => showToast("error", "Failed to load cartridges"))
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => {
    logout();
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <header className="sticky top-0 z-20 glass border-b border-[var(--border)]">
        <div className="max-w-5xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 group">
            <LogoIcon />
            <span className="text-base font-bold tracking-tight" style={{ fontFamily: "var(--font-geist-mono)" }}>
              Starlight
            </span>
          </Link>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Link href="/topics" className="btn btn-ghost text-xs gap-1.5">
                  <TopicIcon />
                  <span className="hidden sm:inline">Topics</span>
                </Link>
                <Link href="/stats" className="btn btn-ghost text-xs gap-1.5">
                  <ChartIcon />
                  <span className="hidden sm:inline">Stats</span>
                </Link>
                <div className="hidden sm:flex items-center gap-2 text-sm text-[var(--text-secondary)] pl-2 border-l border-[var(--border)]">
                  <div className="w-6 h-6 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center text-xs font-semibold">
                    {user.email?.[0]?.toUpperCase() || "U"}
                  </div>
                  <span className="text-xs max-w-[140px] truncate">{user.email}</span>
                </div>
                <div className="relative">
                  <button onClick={() => setMenuOpen(!menuOpen)} className="icon-btn" title="Menu">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
                  </button>
                  {menuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                      <div className="absolute right-0 top-full mt-1 w-44 card p-1.5 z-50 animate-pop">
                        <button onClick={() => { toggleTheme(); setMenuOpen(false); }} className="w-full text-left px-3 py-2 text-sm rounded-lg flex items-center gap-2.5 hover:bg-[var(--border-light)] transition-colors">
                          {dark ? <SunIcon /> : <MoonIcon />}
                          {dark ? "Light mode" : "Dark mode"}
                        </button>
                        <button onClick={() => { handleLogout(); setMenuOpen(false); }} className="w-full text-left px-3 py-2 text-sm rounded-lg flex items-center gap-2.5 hover:bg-[var(--border-light)] text-[var(--error)] transition-colors">
                          <LogOutIcon />
                          Log out
                        </button>
                      </div>
                    </>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link href="/login" className="btn text-xs">Log in</Link>
                <Link href="/register" className="btn btn-primary text-xs">Get started</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--accent-glow)] to-transparent pointer-events-none" />
        <div className="max-w-5xl mx-auto px-4 md:px-6 pt-16 pb-12 md:pt-24 md:pb-16 text-center relative">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--border)] bg-[var(--bg-card)] text-xs text-[var(--text-secondary)] mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
            AI-Powered Learning
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 leading-tight">
            Learn anything through<br />
            <span className="bg-gradient-to-r from-[var(--accent)] to-[var(--accent-light)] bg-clip-text text-transparent">
              conversation
            </span>
          </h1>
          <p className="text-[var(--text-secondary)] text-base md:text-lg max-w-md mx-auto leading-relaxed mb-8">
            Master topics interactively with AI. Ask questions, get quizzed, and build knowledge layer by layer.
          </p>
          <div className="flex items-center justify-center gap-4 text-xs text-[var(--text-muted)]">
            <span className="flex items-center gap-1.5"><BookIcon /> Interactive Lessons</span>
            <span className="flex items-center gap-1.5"><LayersIcon /> Adaptive Path</span>
            <span className="flex items-center gap-1.5"><ChartIcon /> Track Progress</span>
          </div>
        </div>
      </section>

      {/* Grid */}
      <section className="max-w-5xl mx-auto px-4 md:px-6 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <CartridgeSkeleton key={i} />)
          ) : cartridges.map((c) => (
            <Link key={c.id} href={`/learn/${c.id}`}
              className="card p-5 group hover:-translate-y-0.5">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white">
                  <BookIcon />
                </div>
                <span className="badge bg-[var(--accent)]/10 text-[var(--accent)]">v{c.version}</span>
              </div>
              <h2 className="font-semibold text-sm mb-2 group-hover:text-[var(--accent)] transition-colors">
                {c.title}
              </h2>
              <p className="text-xs text-[var(--text-muted)] mb-4 flex items-center gap-1">
                <LayersIcon /> {c.node_count} learning nodes
              </p>
              <div className="flex items-center justify-center gap-1.5 text-xs font-medium text-[var(--accent)] py-2.5 border-t border-[var(--border)] group-hover:bg-[var(--accent)] group-hover:text-white rounded-b-[11px] transition-all -mx-5 -mb-5 mt-auto px-5">
                Start learning <ArrowRightIcon />
              </div>
            </Link>
          ))}
          {!loading && cartridges.length === 0 && (
            <div className="col-span-full text-center text-[var(--text-muted)] py-16">
              <div className="w-12 h-12 rounded-full bg-[var(--border-light)] flex items-center justify-center mx-auto mb-3">
                <LayersIcon />
              </div>
              <p className="text-sm">No cartridges available yet.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
