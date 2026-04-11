"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  type Node as RFNode,
  type Edge as RFEdge,
  type NodeProps,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface NodeInfo {
  id: string;
  title: string;
  difficulty: number;
  prerequisites: string[];
  status: string;
  score: number | null;
}
interface CartridgeData {
  id: string;
  title: string;
  nodes: NodeInfo[];
  progress: { completed: number; total: number };
  dag: Record<string, unknown>;
}

const NODE_W = 220;
const NODE_H = 72;
const GAP_X = 100;
const GAP_Y = 24;

function computeLayout(nodes: NodeInfo[]) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const depth = new Map<string, number>();
  const visited = new Set<string>();

  function getDepth(id: string): number {
    if (depth.has(id)) return depth.get(id)!;
    if (visited.has(id)) return 0;
    visited.add(id);
    const node = nodeMap.get(id);
    if (!node || node.prerequisites.length === 0) { depth.set(id, 0); return 0; }
    const d = Math.max(...node.prerequisites.map(getDepth)) + 1;
    depth.set(id, d);
    return d;
  }
  nodes.forEach((n) => getDepth(n.id));

  const groups = new Map<number, string[]>();
  nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0;
    if (!groups.has(d)) groups.set(d, []);
    groups.get(d)!.push(n.id);
  });

  const positions = new Map<string, { x: number; y: number }>();
  Array.from(groups.keys()).sort((a, b) => a - b).forEach((d) => {
    groups.get(d)!.forEach((id, i) => {
      positions.set(id, { x: d * (NODE_W + GAP_X), y: i * (NODE_H + GAP_Y) });
    });
  });

  return positions;
}

function DagNode({ data }: NodeProps) {
  const nd = data as unknown as { title: string; difficulty: number; status: string; nodeId: string };
  const isCompleted = nd.status === "completed";
  const isProgress = nd.status === "in_progress";

  return (
    <div
      className="cursor-pointer rounded-xl border bg-white px-4 py-3 shadow-sm transition-shadow hover:shadow-md"
      style={{
        width: NODE_W,
        height: NODE_H,
        borderColor: isCompleted ? "var(--success)" : isProgress ? "var(--warning)" : "var(--border)",
        borderWidth: isCompleted || isProgress ? 2 : 1,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "var(--accent)", width: 8, height: 8, border: 'none' }} />
      <div className="flex items-center gap-2 mb-1.5">
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${isCompleted ? "bg-emerald-400" : isProgress ? "bg-amber-400" : "bg-gray-300"}`} />
        <span className="text-xs font-semibold truncate">{nd.title}</span>
      </div>
      <div className="flex items-center gap-2 text-[11px] text-gray-500">
        <span className="px-1.5 py-0.5 rounded-md text-[10px] font-medium" style={{ background: "var(--accent)", color: "#fff" }}>
          Lv.{nd.difficulty}
        </span>
        <span className="truncate">{nd.nodeId}</span>
      </div>
      <Handle type="source" position={Position.Right} style={{ background: "var(--accent)", width: 8, height: 8, border: 'none' }} />
    </div>
  );
}

const nodeTypes = { dagNode: DagNode };

function ChevronLeftIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>; }
function MapIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>; }

export default function DagPage() {
  const params = useParams();
  const router = useRouter();
  const cartridgeId = params.cartridgeId as string;
  const { token } = useAuthStore();
  const [cartridge, setCartridge] = useState<CartridgeData | null>(null);

  useEffect(() => {
    if (token) api.getCartridge(cartridgeId).then(setCartridge).catch(console.error);
  }, [cartridgeId, token]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: RFNode) => {
      router.push(`/learn/${cartridgeId}?node=${node.id}`);
    },
    [router, cartridgeId],
  );

  if (!cartridge) {
    return (
      <div className="h-screen flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="text-sm text-[var(--text-muted)]">Loading...</div>
      </div>
    );
  }

  const positions = computeLayout(cartridge.nodes);

  const rfNodes: RFNode[] = cartridge.nodes.map((n) => ({
    id: n.id,
    type: "dagNode",
    position: positions.get(n.id) ?? { x: 0, y: 0 },
    data: { title: n.title, difficulty: n.difficulty, status: n.status, nodeId: n.id },
  }));

  const rfEdges: RFEdge[] = cartridge.nodes.flatMap((n) =>
    n.prerequisites.map((pre) => ({
      id: `${pre}->${n.id}`,
      source: pre,
      target: n.id,
      animated: true,
      style: { stroke: "var(--accent)", strokeWidth: 1.5 },
    })),
  );

  return (
    <div className="h-screen flex flex-col bg-[var(--bg-primary)]">
      <div className="px-3 md:px-4 py-2.5 border-b border-[var(--border)] glass flex items-center gap-3">
        <button onClick={() => router.push(`/learn/${cartridgeId}`)} className="btn btn-ghost text-xs gap-1 px-2 py-1.5">
          <ChevronLeftIcon /> Back
        </button>
        <div className="flex items-center gap-1.5">
          <MapIcon />
          <h2 className="font-semibold text-sm truncate">{cartridge.title}</h2>
        </div>
        <span className="text-xs text-[var(--text-muted)] ml-auto">
          {cartridge.progress.completed}/{cartridge.progress.total}
        </span>
      </div>
      <div className="flex-1">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.2}
          style={{ background: "var(--bg-primary)" }}
        >
          <Background color="var(--border)" gap={20} size={1} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
