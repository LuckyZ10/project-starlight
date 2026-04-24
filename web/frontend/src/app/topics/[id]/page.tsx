"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { showToast } from "@/components/Toast";

interface Topic {
  id: string;
  name: string;
  description: string | null;
  status: string;
  platforms: string[];
  config: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

/* ─── Icons ─── */
function ArrowLeftIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function FileTextIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function LoaderIcon() {
  return (
    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="2" x2="12" y2="6" />
      <line x1="12" y1="18" x2="12" y2="22" />
      <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
      <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
      <line x1="2" y1="12" x2="6" y2="12" />
      <line x1="18" y1="12" x2="22" y2="12" />
      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
      <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
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
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${colors[status] || colors.draft}`}>
      {status}
    </span>
  );
}

export default function TopicDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [topic, setTopic] = useState<Topic | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (id) loadTopic();
  }, [id]);

  async function loadTopic() {
    try {
      setLoading(true);
      const data = await api.getTopic(id);
      setTopic(data);
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
        if (err.status === 404) router.push("/topics");
      } else {
        showToast("error", "Failed to load topic");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePlan() {
    try {
      setActionLoading("plan");
      await api.generatePlan(id);
      showToast("success", "Plan generation started");
      loadTopic();
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
      } else {
        showToast("error", "Failed to generate plan");
      }
    } finally {
      setActionLoading(null);
    }
  }

  async function handleGenerateContent() {
    try {
      setActionLoading("content");
      await api.generateContent(id);
      showToast("success", "Content generation started");
      loadTopic();
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
      } else {
        showToast("error", "Failed to generate content");
      }
    } finally {
      setActionLoading(null);
    }
  }

  async function handlePublish() {
    try {
      setActionLoading("publish");
      await api.publishTopic(id);
      showToast("success", "Topic published");
      loadTopic();
    } catch (err) {
      if (err instanceof ApiError) {
        showToast("error", err.message);
      } else {
        showToast("error", "Failed to publish");
      }
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="flex items-center gap-2 text-[var(--text-secondary)]">
          <LoaderIcon />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  if (!topic) {
    return (
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--text-secondary)] mb-4">Topic not found</p>
          <Link href="/topics" className="btn btn-primary text-sm">
            Back to Topics
          </Link>
        </div>
      </div>
    );
  }

  const canGeneratePlan = topic.status === "draft" || topic.status === "planning";
  const canGenerateContent = topic.status === "planning" || topic.status === "generating";
  const canPublish = topic.status === "ready" || topic.status === "reviewing";

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Header */}
      <header className="sticky top-0 z-20 glass border-b border-[var(--border)]">
        <div className="max-w-5xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/topics" className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
              <ArrowLeftIcon />
            </Link>
            <h1 className="text-base font-semibold truncate max-w-[200px] sm:max-w-md">{topic.name}</h1>
            <StatusBadge status={topic.status} />
          </div>
          <Link href={`/topics/${id}/edit`} className="btn btn-ghost text-xs">
            Edit
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-4 md:px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <div className="card p-6">
              <h2 className="text-sm font-semibold mb-3">Description</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                {topic.description || "No description provided."}
              </p>
            </div>

            {/* Config */}
            {topic.config && Object.keys(topic.config).length > 0 && (
              <div className="card p-6">
                <h2 className="text-sm font-semibold mb-3">Configuration</h2>
                <pre className="text-xs bg-[var(--bg-secondary)] p-3 rounded-lg overflow-auto">
                  {JSON.stringify(topic.config, null, 2)}
                </pre>
              </div>
            )}

            {/* Platforms */}
            <div className="card p-6">
              <h2 className="text-sm font-semibold mb-3">Target Platforms</h2>
              <div className="flex flex-wrap gap-2">
                {topic.platforms?.map((platform) => (
                  <span key={platform} className="badge bg-[var(--accent)]/10 text-[var(--accent)]">
                    {platform}
                  </span>
                )) || <span className="text-sm text-[var(--text-muted)]">No platforms configured</span>}
              </div>
            </div>
          </div>

          {/* Sidebar Actions */}
          <div className="space-y-4">
            <div className="card p-5">
              <h3 className="text-sm font-semibold mb-4">Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={handleGeneratePlan}
                  disabled={!canGeneratePlan || actionLoading !== null}
                  className="w-full btn btn-primary text-xs gap-1.5 justify-center disabled:opacity-50"
                >
                  {actionLoading === "plan" ? <LoaderIcon /> : <PlayIcon />}
                  Generate Plan
                </button>
                <button
                  onClick={handleGenerateContent}
                  disabled={!canGenerateContent || actionLoading !== null}
                  className="w-full btn btn-ghost text-xs gap-1.5 justify-center disabled:opacity-50"
                >
                  {actionLoading === "content" ? <LoaderIcon /> : <FileTextIcon />}
                  Generate Content
                </button>
                <button
                  onClick={handlePublish}
                  disabled={!canPublish || actionLoading !== null}
                  className="w-full btn btn-ghost text-xs gap-1.5 justify-center disabled:opacity-50"
                >
                  {actionLoading === "publish" ? <LoaderIcon /> : <SendIcon />}
                  Publish
                </button>
              </div>
            </div>

            <div className="card p-5">
              <h3 className="text-sm font-semibold mb-3">Details</h3>
              <div className="space-y-2 text-xs text-[var(--text-secondary)]">
                <div className="flex justify-between">
                  <span>Created</span>
                  <span>{new Date(topic.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Updated</span>
                  <span>{new Date(topic.updated_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>ID</span>
                  <span className="font-mono">{topic.id.slice(0, 8)}...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
