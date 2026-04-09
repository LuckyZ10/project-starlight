export default function ChatSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* AI message skeleton */}
      <div className="max-w-[80%] p-4 pixel-card">
        <div className="h-3 bg-[var(--border-light)] rounded w-3/4 mb-3" />
        <div className="h-3 bg-[var(--border-light)] rounded w-1/2 mb-3" />
        <div className="h-3 bg-[var(--border-light)] rounded w-2/3" />
      </div>
      {/* Question skeleton */}
      <div className="max-w-lg p-6 pixel-card">
        <div className="h-4 bg-[var(--border-light)] rounded w-2/3 mb-4" />
        <div className="space-y-2">
          <div className="h-10 bg-[var(--border-light)] rounded" />
          <div className="h-10 bg-[var(--border-light)] rounded" />
          <div className="h-10 bg-[var(--border-light)] rounded" />
        </div>
      </div>
    </div>
  );
}

export function CartridgeSkeleton() {
  return (
    <div className="pixel-card p-6 animate-pulse">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 bg-[var(--border-light)] rounded" />
        <div className="h-5 bg-[var(--border-light)] rounded w-40" />
      </div>
      <div className="h-3 bg-[var(--border-light)] rounded w-24 mb-4" />
      <div className="h-9 bg-[var(--border-light)] rounded" />
    </div>
  );
}

export function SidebarSkeleton() {
  return (
    <div className="space-y-2 p-4 animate-pulse">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-10 bg-[var(--border-light)] rounded" />
      ))}
    </div>
  );
}
