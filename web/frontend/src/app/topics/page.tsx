"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { showToast } from "@/components/Toast";

interface Topic {
  id: string;
  name: string;
  description: string | null;
  status: string;
  platforms: string[];
  created_at: string;
  updated_at: string;
}

/* ─── Icons ─── */
function PlusIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-600",
    planning: "bg-blue-100 text-blue-600",
    generating: "bg-yellow-100 text-yellow-600",
    reviewing: "bg-purple-100 text-purple-600",
    ready: "bg-green-100 text-green-600",
    published: "bg-emerald-100 text-emerald-600",
    archived: "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || colors.draft}`}>
      {status}
    </span>
  );
}

export default function TopicsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadTopics();
  }, []);

  async function loadTopics() {
    try {
      setLoading(true);
      const data = await api.listTopics();
      setTopics(data || []);
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
      } else {
        showToast("error", "Failed to load topics");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Are you sure you want to delete this topic?")) return;
    try {
      setDeleting(id);
      await api.deleteTopic(id);
      showToast("success", "Topic deleted");
      setTopics(topics.filter((t) => t.id !== id));
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
      } else {
        showToast("error", "Failed to delete topic");
      }
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <header className="sticky top-0 z-20 glass border-b border-[var(--border)]">
        <div className="max-w-5xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
              ← Back
            </Link>
            <h1 className="text-base font-semibold">Topics</h1>
          </div>
          <Link
            href="/topics/new"
            className="btn btn-primary text-xs gap-1.5"
          >
            <PlusIcon />
            New Topic
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 md:px-6 py-8">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card p-5 animate-pulse">
                <div className="h-4 bg-[var(--border-light)] rounded w-1/3 mb-3" />
                <div className="h-3 bg-[var(--border-light)] rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : topics.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-[var(--accent)]/10 flex items-center justify-center mx-auto mb-4">
              <BookIcon />
            </div>
            <h2 className="text-lg font-semibold mb-2">No topics yet</h2>
            <p className="text-sm text-[var(--text-secondary)] mb-6 max-w-sm mx-auto">
              Create your first learning topic to get started with AI-powered content generation.
            </p>
            <Link href="/topics/new" className="btn btn-primary text-sm gap-1.5 inline-flex">
              <PlusIcon />
              Create Topic
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {topics.map((topic) => (
              <div
                key={topic.id}
                className="card p-5 group hover:-translate-y-0.5 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h2 className="font-semibold text-sm truncate">{topic.name}</h2>
                      <StatusBadge status={topic.status} />
                    </div>
                    {topic.description && (
                      <p className="text-xs text-[var(--text-secondary)] mb-3 line-clamp-2">
                        {topic.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                      <span>{topic.platforms?.length || 0} platforms</span>
                      <span>•</span>
                      <span>{new Date(topic.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Link
                      href={`/topics/${topic.id}`}
                      className="btn btn-ghost text-xs gap-1"
                    >
                      View <ArrowRightIcon />
                    </Link>
                    <button
                      onClick={() => handleDelete(topic.id)}
                      disabled={deleting === topic.id}
                      className="btn btn-ghost text-xs text-[var(--error)] hover:bg-[var(--error)]/10"
                    >
                      {deleting === topic.id ? "..." : "Delete"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
