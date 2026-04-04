# starlight/core/session.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Exchange:
    """一轮对话"""
    role: str           # "system" | "assistant" | "user"
    content: str
    metadata: dict | None = None  # verdict, score, strategy 等
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    """一次学习会话 — 管理完整对话历史和节点状态"""
    user_id: int
    cartridge_id: str
    current_node: str
    conversation: list[Exchange] = field(default_factory=list)
    turn_count: int = 0
    max_turns: int = 5     # 默认每节点最多5轮对话
    node_scores: dict[str, list[int]] = field(default_factory=dict)  # node_id -> scores
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_exchange(self, role: str, content: str, metadata: dict | None = None) -> Exchange:
        ex = Exchange(role=role, content=content, metadata=metadata)
        self.conversation.append(ex)
        if role == "user":
            self.turn_count += 1
        return ex
    
    def get_context_window(self, max_messages: int = 20) -> list[dict]:
        """获取最近的对话上下文（用于 LLM 调用）"""
        recent = self.conversation[-max_messages:]
        return [{"role": ex.role, "content": ex.content} for ex in recent]
    
    def get_current_exchange_count(self) -> int:
        """当前节点已经过几轮用户回答"""
        return self.turn_count
    
    def should_force_verdict(self) -> bool:
        """是否应该强制判定（达到最大轮数）"""
        return self.turn_count >= self.max_turns
    
    def reset_for_new_node(self, node_id: str) -> None:
        """进入新节点时重置"""
        if self.current_node not in self.node_scores:
            self.node_scores[self.current_node] = []
        self.current_node = node_id
        self.conversation.clear()
        self.turn_count = 0
    
    def record_score(self, node_id: str, score: int) -> None:
        if node_id not in self.node_scores:
            self.node_scores[node_id] = []
        self.node_scores[node_id].append(score)
    
    def get_avg_score(self, node_id: str) -> float:
        scores = self.node_scores.get(node_id, [])
        return sum(scores) / len(scores) if scores else 0.0
    
    def advance_node(self, new_node: str) -> None:
        self.reset_for_new_node(new_node)
    
    @property
    def last_exchange(self) -> Exchange | None:
        return self.conversation[-1] if self.conversation else None
