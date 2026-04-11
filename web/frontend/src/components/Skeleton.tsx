export default function ChatSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="flex gap-2.5">
        <div className="w-7 h-7 rounded-full bg-[var(--border)] shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-[var(--border)] rounded w-3/4" />
          <div className="h-3 bg-[var(--border)] rounded w-1/2" />
          <div className="h-3 bg-[var(--border)] rounded w-2/3" />
        </div>
      </div>
    </div>
  );
}

export function CartridgeSkeleton() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-[var(--border)]" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-[var(--border)] rounded w-3/4" />
          <div className="h-3 bg-[var(--border)] rounded w-1/3" />
        </div>
      </div>
      <div className="h-9 bg-[var(--border)] rounded-lg" />
    </div>
  );
}

export function SidebarSkeleton() {
  return (
    <div className="space-y-2 p-4 animate-pulse">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-10 bg-[var(--border)] rounded-lg" />
      ))}
    </div>
  );
}
