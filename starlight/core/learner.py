# starlight/core/learner.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ZPDZone(str, Enum):
    BELOW = "below"      # 低于 ZPD，太简单
    ZPD = "zpd"          # 在 ZPD 内，最佳学习区
    ABOVE = "above"      # 高于 ZPD，太难


@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str      # "concept" | "calculation" | "application" | "attention"
    count: int = 0
    last_seen_node: str = ""
    remediation: str = ""


@dataclass
class LearnerProfile:
    """学习者画像 — 融合启智 learner-model 十维度"""
    user_id: int
    
    # 核心维度
    knowledge_level: float = 0.0      # 0-1 知识水平
    learning_speed: float = 1.0       # 0.5-1.5 学习速度
    confidence: float = 0.5           # 0-1 自信度
    engagement: float = 0.5           # 0-1 参与度
    cognitive_load: float = 0.3       # 0-1 认知负荷
    
    # ZPD
    zpd_zone: ZPDZone = ZPDZone.ZPD
    
    # 布鲁姆层次（当前能达到的最高层次）
    bloom_level: int = 1              # 1-6
    
    # 游戏化
    streak_days: int = 0
    total_xp: int = 0
    nodes_completed: int = 0
    
    # 错误模式
    error_patterns: list[ErrorPattern] = field(default_factory=list)
    
    # 学习历史摘要
    history: dict[str, Any] = field(default_factory=dict)
    
    def update_from_assessment(self, score: int, verdict: str, turn_count: int, error_type: str | None = None) -> None:
        """根据一次考核结果更新画像"""
        # 更新知识水平（加权移动平均）
        alpha = 0.3
        self.knowledge_level = alpha * (score / 100) + (1 - alpha) * self.knowledge_level
        
        # 更新自信度
        if verdict == "PASS":
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.confidence = max(0.0, self.confidence - 0.03)
        
        # 更新参与度（对话轮数越多参与度越高）
        self.engagement = min(1.0, 0.3 + turn_count * 0.15)
        
        # 更新布鲁姆层次
        if score >= 85 and self.bloom_level < 6:
            self.bloom_level = min(6, self.bloom_level + 1)
        
        # 更新 ZPD
        self._update_zpd(score)
        
        # 记录错误
        if error_type and verdict == "FAIL":
            self._record_error(error_type)
        
        # 更新 XP
        if verdict == "PASS":
            xp = self._calculate_xp(score)
            self.total_xp += xp
            self.nodes_completed += 1
    
    def get_difficulty_modifier(self) -> float:
        """根据 ZPD 和认知负荷计算难度调节因子"""
        if self.zpd_zone == ZPDZone.BELOW:
            return 0.7  # 降低难度
        elif self.zpd_zone == ZPDZone.ABOVE:
            return 1.3  # 仍然高难度，但给更多提示
        return 1.0  # ZPD 内，正常难度
    
    def should_get_hint(self) -> bool:
        """是否应该给提示"""
        return self.cognitive_load > 0.7 or self.zpd_zone == ZPDZone.ABOVE
    
    def get_max_turns(self) -> int:
        """根据学习者状态推荐最大对话轮数"""
        base = 5
        if self.learning_speed < 0.8:
            return base + 2  # 学得慢，多给几轮
        if self.confidence < 0.3:
            return base + 1  # 不自信，多引导
        return base
    
    def _update_zpd(self, score: int) -> None:
        if score >= 90:
            self.zpd_zone = ZPDZone.BELOW  # 太简单了
        elif score >= 50:
            self.zpd_zone = ZPDZone.ZPD    # 恰好
        else:
            self.zpd_zone = ZPDZone.ABOVE  # 太难了
    
    def _record_error(self, error_type: str) -> None:
        for pattern in self.error_patterns:
            if pattern.error_type == error_type:
                pattern.count += 1
                return
        self.error_patterns.append(ErrorPattern(error_type=error_type, count=1))
    
    def _calculate_xp(self, score: int) -> int:
        """XP 计算（启智 gamification skill）"""
        base = 100
        difficulty = 1.0 + (self.bloom_level - 1) * 0.2
        quality = score / 100
        streak_bonus = min(self.streak_days * 0.1, 1.0)
        return round(base * difficulty * quality * (1 + streak_bonus))
    
    def get_warning(self) -> str | None:
        """动机预警（启智 motivation-tracker）"""
        if self.confidence < 0.2:
            return "⚠️ 学习者自信心过低，建议降低难度或给予鼓励"
        if self.engagement < 0.2:
            return "⚠️ 参与度过低，可能失去兴趣"
        consecutive_errors = sum(1 for p in self.error_patterns if p.count >= 3)
        if consecutive_errors >= 2:
            return "⚠️ 多个错误模式频繁出现，建议回顾基础"
        return None
