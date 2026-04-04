# starlight/core/spaced_rep.py
"""SM-2+ 间隔重复算法 — 融合启智 spaced-repetition skill"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
import math


@dataclass
class ReviewCard:
    """复习卡片"""
    node_id: str
    cartridge_id: str
    interval: int = 1           # 当前间隔（天）
    ease_factor: float = 2.5    # 难度因子
    repetition: int = 0         # 连续正确次数
    last_review: datetime | None = None
    next_review: datetime | None = None
    title: str = ""


def calculate_next_review(card: ReviewCard, quality: int) -> ReviewCard:
    """SM-2+ 算法计算下次复习时间
    
    Args:
        card: 复习卡片
        quality: 回答质量 (0-5)
            5 = 完美
            4 = 正确但有些犹豫
            3 = 正确但很困难
            2 = 错误但有些印象
            1 = 错误且毫无印象
            0 = 完全不记得
    
    Returns:
        更新后的 ReviewCard
    """
    now = datetime.utcnow()
    
    # 更新难度因子
    card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    
    if quality >= 3:
        # 正确回答
        if card.repetition == 0:
            card.interval = 1
        elif card.repetition == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.ease_factor)
        card.repetition += 1
    else:
        # 错误回答 → 重置
        card.repetition = 0
        card.interval = 1
    
    card.last_review = now
    card.next_review = now + timedelta(days=card.interval)
    
    return card


def get_due_cards(cards: list[ReviewCard], now: datetime | None = None) -> list[ReviewCard]:
    """获取到期需要复习的卡片"""
    if now is None:
        now = datetime.utcnow()
    return sorted(
        [c for c in cards if c.next_review and c.next_review <= now],
        key=lambda c: c.next_review or now
    )


def retention_rate(days_since_review: int, ease_factor: float) -> float:
    """计算记忆保持率 R = e^(-t/S)"""
    S = ease_factor * 10  # 简化的记忆强度
    return math.exp(-days_since_review / S)
