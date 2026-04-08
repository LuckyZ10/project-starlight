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
const NODE_H = 80;
const GAP_X = 100;
const GAP_Y = 30;

function computeLayout(nodes: NodeInfo[]) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  // Compute depth (max distance from root)
  const depth = new Map<string, number>();
  const visited = new Set<string>();

  function getDepth(id: string): number {
    if (depth.has(id)) return depth.get(id)!;
    if (visited.has(id)) return 0; // cycle guard
    visited.add(id);
    const node = nodeMap.get(id);
    if (!node || node.prerequisites.length === 0) {
      depth.set(id, 0);
      return 0;
    }
    const d = Math.max(...node.prerequisites.map(getDepth)) + 1;
    depth.set(id, d);
    return d;
  }
  nodes.forEach((n) => getDepth(n.id));

  // Group by depth
  const groups = new Map<number, string[]>();
  nodes.forEach((n) => {
    const d = depth.get(n.id) ?? 0;
    if (!groups.has(d)) groups.set(d, []);
    groups.get(d)!.push(n.id);
  });

  const positions = new Map<string, { x: number; y: number }>();
  const sortedDepths = Array.from(groups.keys()).sort((a, b) => a - b);
  sortedDepths.forEach((d) => {
    const ids = groups.get(d)!;
    ids.forEach((id, i) => {
      positions.set(id, {
        x: d * (NODE_W + GAP_X),
        y: i * (NODE_H + GAP_Y),
      });
    });
  });

  return positions;
}

function statusColor(status: string) {
  if (status === "completed") return "#55efc4";
  if (status === "in_progress") return "#ffeaa7";
  return "#dfe6e9";
}

function statusEmoji(status: string) {
  if (status === "completed") return "🟩";
  if (status === "in_progress") return "🟨";
  return "⬜";
}

function DagNode({ data }: NodeProps) {
  const nd = data as unknown as {
    title: string;
    difficulty: number;
    status: string;
    nodeId: string;
  };
  return (
    <div
      className="cursor-pointer rounded-lg border-2 px-3 py-2"
      style={{
        width: NODE_W,
        height: NODE_H,
        borderColor: "#00b894",
        background: statusColor(nd.status),
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: "#00b894" }} />
      <div className="flex items-center gap-1 mb-1">
        <span>{statusEmoji(nd.status)}</span>
        <span className="text-xs font-bold truncate">{nd.title}</span>
      </div>
      <div className="flex items-center gap-2 text-xs text-gray-600">
        <span className="px-1 rounded" style={{ background: "#00b894", color: "#fff" }}>
          Lv.{nd.difficulty}
        </span>
        <span>{nd.nodeId}</span>
      </div>
      <Handle type="source" position={Position.Right} style={{ background: "#00b894" }} />
    </div>
  );
}

const nodeTypes = { dagNode: DagNode };

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
      <div className="h-screen flex items-center justify-center" style={{ background: "#f5f6fa" }}>
        <div className="text-2xl">⏳ Loading DAG...</div>
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
      style: { stroke: "#00b894", strokeWidth: 2 },
    })),
  );

  return (
    <div className="h-screen flex flex-col" style={{ background: "#f5f6fa" }}>
      <div className="px-4 py-3 border-b-2 border-[var(--border)] bg-white flex items-center gap-4">
        <button
          onClick={() => router.push(`/learn/${cartridgeId}`)}
          className="pixel-btn pixel-btn-primary text-sm"
        >
          ← Back to Chat
        </button>
        <h2 className="font-bold text-sm" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          🗺️ DAG — {cartridge.title}
        </h2>
        <span className="text-xs text-[var(--text-muted)]">
          {cartridge.progress.completed}/{cartridge.progress.total} completed
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
          style={{ background: "#f5f6fa" }}
        >
          <Background color="#00b894" gap={20} size={1} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
