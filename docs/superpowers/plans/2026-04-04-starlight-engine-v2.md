# Phase 2.5: 学习引擎深度改造 — 启智 Skill 融合 + OpenHarness 架构借鉴

**目标：** 把启智 24 个教学 skill 的核心理念融入 Starlight 的学习交互，同时借鉴 OpenHarness 的 Harness 架构模式（Agent Loop、Skills System、Memory、Plugin），让 Starlight 从"甩教材 + 判断对错"变成真正的智能教学引擎。

**架构思路：**
- **借鉴 OpenHarness 的 Agent Loop** → Starlight 的教学循环：呈现 → 提问 → 回答 → 评估 → 反馈 → 循环
- **借鉴 OpenHarness 的 Skills System** → 教学策略作为可插拔 skill（苏格拉底、费曼、间隔重复等）
- **借鉴 OpenHarness 的 Memory** → 学习者画像 + 会话记忆持久化
- **融合启智教学 skill** → 12 个核心教学策略融入 Assessor 和 Harness

**技术栈：** Python 3.10+, LiteLLM, pytest（不变）

**工作目录：** `/tmp/project-starlight/`

---

## 当前问题诊断

| 问题 | 根因 | 对应启智 Skill |
|------|------|---------------|
| 每次回答都是空对话历史 | 没有会话记忆 | — |
| 直接甩教材让用户回答 | 没有引导式提问 | socratic-dialogue, question-design |
| 一次判定太粗暴 | 没有多轮评估策略 | assessment, difficulty-adjuster |
| 所有人同样难度 | 没有自适应 | adaptive-learning, learner-model |
| 没有反馈策略 | 反馈太简单 | feedback-system, error-analyzer |
| 没有复习机制 | 学完就忘 | spaced-repetition |
| 没有动机维持 | 纯干货无聊 | gamification, motivation-tracker |

---

## 文件结构（新增/修改）

```
starlight/
├── core/
│   ├── harness.py              # [重构] 完整教学循环
│   ├── assessor.py             # [重构] 多策略考核引擎
│   ├── session.py              # [新建] 会话管理（对话记忆 + 状态）
│   ├── learner.py              # [新建] 学习者模型（ZPD + 画像）
│   ├── strategies.py           # [新建] 教学策略系统（可插拔）
│   └── spaced_rep.py           # [新建] SM-2+ 间隔重复
├── adapters/
│   └── telegram_adapter.py     # [修改] 适配新的会话式交互
└── ...

tests/
├── test_session.py             # [新建]
├── test_learner.py             # [新建]
├── test_strategies.py          # [新建]
├── test_spaced_rep.py          # [新建]
├── test_assessor_v2.py         # [新建] 新 Assessor 测试
└── test_harness_v2.py          # [新建] 新 Harness 集成测试
```

---

## 核心设计决策

### 1. 教学循环（借鉴 OpenHarness Agent Loop）

OpenHarness 的核心是 Agent Loop：
```
while True:
    response = await api.stream(messages, tools)
    if response.stop_reason != "tool_use": break
    result = await execute_tool(tool_call)
    messages.append(result)
```

Starlight 的教学循环：
```
while node_not_completed:
    # 1. 呈现阶段：策略决定怎么展示知识
    presentation = strategy.present(node, learner_state)
    # 2. 提问阶段：策略生成引导性问题
    question = strategy.generate_question(node, learner_state)
    # 3. 用户回答
    answer = await get_user_input()
    # 4. 评估阶段：Assessor 判定（多轮对话）
    result = await assessor.assess(node, conversation, answer)
    # 5. 反馈阶段：策略生成反馈
    feedback = strategy.generate_feedback(result, learner_state)
    # 6. 状态更新
    conversation.append({answer, result})
    learner_state.update(result)
```

### 2. 教学策略系统（借鉴 OpenHarness Skills System）

```python
class TeachingStrategy(ABC):
    """可插拔教学策略基类"""
    @abstractmethod
    async def present(self, node, learner) -> str: ...
    
    @abstractmethod
    async def generate_question(self, node, learner, conversation) -> str: ...
    
    @abstractmethod
    async def assess_response(self, node, conversation, answer, learner) -> AssessmentResult: ...
    
    @abstractmethod
    async def generate_feedback(self, result, learner) -> str: ...

class SocraticStrategy(TeachingStrategy): ...    # 苏格拉底式提问
class FeynmanStrategy(TeachingStrategy): ...      # 费曼技巧
class ScaffoldStrategy(TeachingStrategy): ...     # 脚手架教学
class AdaptiveStrategy(TeachingStrategy): ...     # 自适应混合策略
```

### 3. 学习者模型（融合启智 learner-model）

```python
class LearnerProfile:
    user_id: int
    knowledge_level: float       # 0-1 (启智: 知识水平)
    learning_speed: float        # 0.5-1.5 (启智: 学习速度)
    confidence: float            # 0-1 (启智: 自信度)
    engagement: float            # 0-1 (启智: 参与度)
    cognitive_load: float        # 0-1 (启智: 认知负荷)
    zpd_zone: str                # "below" / "zpd" / "above"
    bloom_level: int             # 1-6 布鲁姆层次
    streak_days: int             # 连续学习天数
    total_xp: int                # 总 XP
    error_patterns: list         # 错误模式（启智: error-analyzer）
    
    def get_difficulty_modifier(self) -> float:
        """根据 ZPD 和认知负荷计算难度调节因子"""
        
    def get_preferred_strategy(self) -> type[TeachingStrategy]:
        """根据画像推荐最佳教学策略"""
```

### 4. 会话管理（借鉴 OpenHarness Memory）

```python
class Session:
    """一次学习会话"""
    user_id: int
    cartridge_id: str
    current_node: str
    conversation: list[dict]     # 完整对话历史
    turn_count: int              # 当前节点对话轮数
    max_turns: int               # 最大轮数（启智: 自适应调整）
    
    def add_exchange(self, role, content, metadata=None): ...
    def get_context_window(self, max_messages=20) -> list[dict]: ...
    def should_force_verdict(self) -> bool: ...
```

---

## 并行分组

按独立域分为 **3 个并行流**：

**流 A：核心引擎重构**（Task 1-3）— Session + Learner + Strategies
**流 B：Assessor + Harness 重构**（Task 4-5）— 新 Assessor + 新 Harness
**流 C：辅助系统**（Task 6）— 间隔重复 + 游戏化

---

## 任务 1（流 A）：会话管理 + 学习者模型

**文件：**
- 创建：`starlight/core/session.py`
- 创建：`starlight/core/learner.py`
- 创建：`tests/test_session.py`
- 创建：`tests/test_learner.py`

### session.py

```python
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
```

### learner.py

```python
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
```

### 测试

```python
# tests/test_session.py
from starlight.core.session import Session, Exchange


def test_session_add_exchange():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("system", "Welcome")
    s.add_exchange("user", "Hello")
    assert len(s.conversation) == 2
    assert s.turn_count == 1


def test_context_window():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    for i in range(25):
        s.add_exchange("user", f"msg {i}")
    ctx = s.get_context_window(max_messages=10)
    assert len(ctx) == 10


def test_force_verdict():
    s = Session(user_id=1, cartridge_id="py", current_node="N01", max_turns=3)
    for i in range(3):
        s.add_exchange("user", f"answer {i}")
    assert s.should_force_verdict() is True


def test_reset_for_new_node():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("user", "answer")
    s.reset_for_new_node("N02")
    assert s.current_node == "N02"
    assert len(s.conversation) == 0
    assert s.turn_count == 0
```

```python
# tests/test_learner.py
from starlight.core.learner import LearnerProfile, ZPDZone


def test_initial_state():
    learner = LearnerProfile(user_id=1)
    assert learner.knowledge_level == 0.0
    assert learner.zpd_zone == ZPDZone.ZPD


def test_update_from_pass():
    learner = LearnerProfile(user_id=1)
    learner.update_from_assessment(score=85, verdict="PASS", turn_count=3)
    assert learner.knowledge_level > 0
    assert learner.confidence > 0.5
    assert learner.total_xp > 0
    assert learner.nodes_completed == 1


def test_update_from_fail():
    learner = LearnerProfile(user_id=1, confidence=0.5)
    learner.update_from_assessment(score=30, verdict="FAIL", turn_count=5, error_type="concept")
    assert learner.confidence < 0.5
    assert learner.zpd_zone == ZPDZone.ABOVE
    assert len(learner.error_patterns) == 1


def test_difficulty_modifier():
    learner = LearnerProfile(user_id=1, zpd_zone=ZPDZone.BELOW)
    assert learner.get_difficulty_modifier() < 1.0
    learner.zpd_zone = ZPDZone.ABOVE
    assert learner.get_difficulty_modifier() > 1.0


def test_zpd_transition():
    learner = LearnerProfile(user_id=1)
    learner.update_from_assessment(score=95, verdict="PASS", turn_count=1)
    assert learner.zpd_zone == ZPDZone.BELOW
    learner.update_from_assessment(score=40, verdict="FAIL", turn_count=5)
    assert learner.zpd_zone == ZPDZone.ABOVE


def test_warning():
    learner = LearnerProfile(user_id=1, confidence=0.1)
    assert learner.get_warning() is not None
```

### Commit

```bash
git add -A && git commit -m "feat: session management and learner profile with ZPD + gamification"
```

---

## 任务 2（流 A）：教学策略系统

**文件：**
- 创建：`starlight/core/strategies.py`
- 创建：`tests/test_strategies.py`

### strategies.py

```python
# starlight/core/strategies.py
"""可插拔教学策略系统 — 融合启智 12 个教学方法"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class TeachingStrategy(ABC):
    """教学策略基类"""
    
    name: str = "base"
    description: str = ""
    
    @abstractmethod
    async def build_system_prompt(self, node_content: str, pass_criteria: str, 
                                   learner: Any, session: Any) -> str:
        """构建 LLM system prompt"""
    
    @abstractmethod
    def should_pass(self, llm_response: str, turn_count: int, max_turns: int, 
                    learner: Any) -> tuple[bool, str]:
        """解析 LLM 回复，决定是否通过。返回 (passed, feedback)"""
    
    def get_opening_message(self, node_title: str, node_content: str, learner: Any) -> str:
        """生成开场白（不直接甩教材）"""
        return f"📚 今天我们来学习「{node_title}」\n\n我准备了一个场景来考考你，准备好了吗？直接回答就好！"


class SocraticStrategy(TeachingStrategy):
    """苏格拉底策略 — 通过提问引导学习者自己发现答案
    
    融合启智 skill:
    - socratic-dialogue: 提问类型库、引导模板
    - question-design: 布鲁姆层次题目设计
    - feedback-system: 反馈策略
    """
    
    name = "socratic"
    description = "苏格拉底式提问引导"
    
    async def build_system_prompt(self, node_content, pass_criteria, learner, session):
        learner_desc = self._describe_learner(learner)
        force_hint = ""
        if session.should_force_verdict():
            force_hint = "\n\n⚠️ 这是最后一轮了，你必须做出判定：[PASS] 或 [FAIL]。"
        
        difficulty_hint = ""
        mod = learner.get_difficulty_modifier() if learner else 1.0
        if mod < 1.0:
            difficulty_hint = "\n难度调整：学习者基础较弱，用更简单的场景和更多提示。"
        elif mod > 1.0:
            difficulty_hint = "\n难度调整：学习者水平较高，用更有挑战的场景。"
        
        hint_instruction = ""
        if learner and learner.should_get_hint():
            hint_instruction = "\n注意：学习者当前认知负荷较高，在追问时给出明确的方向性提示。"
        
        return f"""你是星光学习机的考核官，使用苏格拉底式教学法。

## 你的角色
你不是在"考"学生，而是在通过对话帮助学生学习。用提问引导他们自己发现答案。

## 考核规则
1. **创设场景**：不要直接问教材里的问题，用真实生活场景让学习者应用知识
2. **引导式提问**：如果回答不完整，不要说"错了"，而是用一个新问题引导他们思考
3. **循序渐进**：从简单概念开始，逐步加深
4. **追问策略**：
   - 回答模糊 → 澄清性问题（"你能举个例子吗？"）
   - 回答错误 → 假设性问题（"如果反过来会怎样？"）
   - 回答正确但不深入 → 探究性问题（"为什么这样？"）
5. **判定时机**：
   - 学习者表现出理解 → 输出 [PASS]
   - 多轮后仍不理解 → 输出 [FAIL] 并给出提示
   - 还需要继续引导 → 继续提问（不输出判定标签）
6. **绝不直接告诉答案**，只给方向性提示

## 知识内容
{node_content}

## 通过标准
{pass_criteria}

## 学习者状态
{learner_desc}
{difficulty_hint}{hint_instruction}{force_hint}"""

    def should_pass(self, llm_response, turn_count, max_turns, learner):
        upper = llm_response.upper()
        if "[PASS]" in upper:
            return True, llm_response
        if "[FAIL]" in upper:
            return False, llm_response
        # 未判定 = 继续对话
        return None, llm_response

    def get_opening_message(self, node_title, node_content, learner):
        return (
            f"🌟 我们来学「{node_title}」！\n\n"
            f"我会用一个场景来考考你，看看你能不能自己发现其中的原理。"
            f"准备好了就直接回答我的问题吧！"
        )

    def _describe_learner(self, learner) -> str:
        if not learner:
            return "新学习者，暂无数据"
        zpd = {"below": "偏低（内容偏简单）", "zpd": "恰好（最佳学习区）", "above": "偏高（需要更多帮助）"}
        return (
            f"知识水平：{learner.knowledge_level:.0%} | "
            f"自信度：{learner.confidence:.0%} | "
            f"布鲁姆层次：L{learner.bloom_level} | "
            f"ZPD：{zpd.get(learner.zpd_zone.value, '未知')}"
        )


class FeynmanStrategy(TeachingStrategy):
    """费曼技巧策略 — 让学习者"教"来检验理解
    
    融合启智 skill:
    - teaching-methods: 费曼技巧四步法
    - explanation-optimizer: 讲解优化
    """
    
    name = "feynman"
    description = "费曼技巧 — 用教来学"
    
    async def build_system_prompt(self, node_content, pass_criteria, learner, session):
        force_hint = ""
        if session and session.should_force_verdict():
            force_hint = "\n\n⚠️ 最后一轮了，判定 [PASS] 或 [FAIL]。"
        
        return f"""你是星光学习机的考核官，使用费曼技巧教学法。

## 你的角色
让学习者用自己的话"教"你。如果他们能简单清楚地解释，说明真懂了。

## 考核规则
1. **要求解释**：请学习者用自己的话解释概念，就像教一个完全不懂的人
2. **追查缺口**：如果解释不清楚，追问具体哪里说不下去
3. **简化测试**：如果用了专业术语，要求用日常语言重新解释
4. **类比测试**：要求学习者想一个日常生活的类比
5. 判定：
   - 能简单清晰地解释 → [PASS]
   - 关键概念说不清楚 → [FAIL]
   - 需要更多引导 → 继续提问

## 知识内容
{node_content}

## 通过标准
{pass_criteria}{force_hint}"""

    def should_pass(self, llm_response, turn_count, max_turns, learner):
        upper = llm_response.upper()
        if "[PASS]" in upper:
            return True, llm_response
        if "[FAIL]" in upper:
            return False, llm_response
        return None, llm_response

    def get_opening_message(self, node_title, node_content, learner):
        return (
            f"🧠 今天学「{node_title}」！\n\n"
            f"我来考考你：假设你要把这个概念教给一个 12 岁的孩子，你会怎么解释？"
        )


class ScaffoldStrategy(TeachingStrategy):
    """脚手架策略 — 分步骤逐步引导
    
    融合启智 skill:
    - teaching-methods: 脚手架教学
    - cognitive-load: 认知负荷控制
    """
    
    name = "scaffold"
    description = "脚手架教学 — 分步引导"
    
    async def build_system_prompt(self, node_content, pass_criteria, learner, session):
        return f"""你是星光学习机的考核官，使用脚手架教学法。

## 你的角色
把复杂的知识拆解成小步骤，每一步给适当的支持，逐步撤除支持。

## 考核规则
1. **分解任务**：把通过标准拆成 2-3 个小目标
2. **逐步引导**：先给示例 → 再给半完成示例 → 最后让学习者独立完成
3. **及时反馈**：每完成一步立即确认
4. **撤除支持**：随着学习者进步，减少提示
5. 判定：
   - 能独立完成最终任务 → [PASS]
   - 需要太多帮助 → [FAIL] 并说明缺什么
   - 还在中间步骤 → 继续引导

## 知识内容
{node_content}

## 通过标准
{pass_criteria}"""

    def should_pass(self, llm_response, turn_count, max_turns, learner):
        upper = llm_response.upper()
        if "[PASS]" in upper:
            return True, llm_response
        if "[FAIL]" in upper:
            return False, llm_response
        return None, llm_response


class AdaptiveStrategy(TeachingStrategy):
    """自适应策略 — 根据学习者画像动态选择策略
    
    融合启智 skill:
    - adaptive-learning: 自适应学习路径
    - difficulty-adjuster: 动态难度调整
    - learner-model: ZPD 判断
    """
    
    name = "adaptive"
    description = "自适应混合策略"
    
    # 内部策略组合
    _strategies = {
        "socratic": SocraticStrategy(),
        "feynman": FeynmanStrategy(),
        "scaffold": ScaffoldStrategy(),
    }
    
    def _select_strategy(self, learner) -> TeachingStrategy:
        """根据学习者画像选择策略"""
        if not learner:
            return self._strategies["socratic"]
        
        # 新手或低自信 → 脚手架
        if learner.knowledge_level < 0.3 or learner.confidence < 0.3:
            return self._strategies["scaffold"]
        
        # 高水平 → 费曼技巧
        if learner.knowledge_level > 0.7 and learner.bloom_level >= 3:
            return self._strategies["feynman"]
        
        # 默认 → 苏格拉底
        return self._strategies["socratic"]
    
    async def build_system_prompt(self, node_content, pass_criteria, learner, session):
        strategy = self._select_strategy(learner)
        return await strategy.build_system_prompt(node_content, pass_criteria, learner, session)
    
    def should_pass(self, llm_response, turn_count, max_turns, learner):
        strategy = self._select_strategy(learner)
        return strategy.should_pass(llm_response, turn_count, max_turns, learner)
    
    def get_opening_message(self, node_title, node_content, learner):
        strategy = self._select_strategy(learner)
        return strategy.get_opening_message(node_title, node_content, learner)


# 策略注册表
STRATEGY_REGISTRY: dict[str, type[TeachingStrategy]] = {
    "socratic": SocraticStrategy,
    "feynman": FeynmanStrategy,
    "scaffold": ScaffoldStrategy,
    "adaptive": AdaptiveStrategy,
}


def get_strategy(name: str = "adaptive") -> TeachingStrategy:
    """获取教学策略实例"""
    cls = STRATEGY_REGISTRY.get(name, AdaptiveStrategy)
    return cls()
```

### 测试

```python
# tests/test_strategies.py
import pytest
from starlight.core.strategies import (
    SocraticStrategy, FeynmanStrategy, ScaffoldStrategy,
    AdaptiveStrategy, get_strategy
)
from starlight.core.learner import LearnerProfile, ZPDZone
from starlight.core.session import Session


@pytest.fixture
def novice():
    return LearnerProfile(user_id=1, knowledge_level=0.1, confidence=0.2)


@pytest.fixture
def expert():
    return LearnerProfile(user_id=2, knowledge_level=0.8, confidence=0.9, bloom_level=4)


@pytest.fixture
def session():
    return Session(user_id=1, cartridge_id="py", current_node="N01")


@pytest.mark.asyncio
async def test_socratic_builds_prompt(novice, session):
    s = SocraticStrategy()
    prompt = await s.build_system_prompt("变量是存数据的", "能写赋值语句", novice, session)
    assert "苏格拉底" in prompt
    assert "变量是存数据的" in prompt


@pytest.mark.asyncio
async def test_socratic_pass():
    s = SocraticStrategy()
    passed, feedback = s.should_pass("很好！[PASS]", 1, 5, None)
    assert passed is True


@pytest.mark.asyncio
async def test_socratic_continue():
    s = SocraticStrategy()
    passed, feedback = s.should_pass("你能举个例子吗？", 1, 5, None)
    assert passed is None


@pytest.mark.asyncio
async def test_feynman_opening():
    s = FeynmanStrategy()
    msg = s.get_opening_message("变量", "内容", None)
    assert "12" in msg


@pytest.mark.asyncio
async def test_adaptive_selects_scaffold_for_novice(novice):
    s = AdaptiveStrategy()
    inner = s._select_strategy(novice)
    assert isinstance(inner, ScaffoldStrategy)


@pytest.mark.asyncio
async def test_adaptive_selects_feynman_for_expert(expert):
    s = AdaptiveStrategy()
    inner = s._select_strategy(expert)
    assert isinstance(inner, FeynmanStrategy)


@pytest.mark.asyncio
async def test_adaptive_selects_socratic_default():
    s = AdaptiveStrategy()
    learner = LearnerProfile(user_id=3, knowledge_level=0.5, confidence=0.6)
    inner = s._select_strategy(learner)
    assert isinstance(inner, SocraticStrategy)


def test_get_strategy():
    s = get_strategy("socratic")
    assert isinstance(s, SocraticStrategy)
    s2 = get_strategy("unknown")
    assert isinstance(s2, AdaptiveStrategy)


@pytest.mark.asyncio
async def test_force_verdict_in_prompt(novice):
    session = Session(user_id=1, cartridge_id="py", current_node="N01", max_turns=2)
    session.add_exchange("user", "a1")
    session.add_exchange("user", "a2")
    s = SocraticStrategy()
    prompt = await s.build_system_prompt("内容", "标准", novice, session)
    assert "最后一轮" in prompt
```

### Commit

```bash
git add -A && git commit -m "feat: pluggable teaching strategies (Socratic, Feynman, Scaffold, Adaptive)"
```

---

## 任务 3（流 A）：间隔重复 + 游戏化

**文件：**
- 创建：`starlight/core/spaced_rep.py`
- 创建：`tests/test_spaced_rep.py`

### spaced_rep.py

```python
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
```

### 测试

```python
# tests/test_spaced_rep.py
from datetime import datetime, timedelta
from starlight.core.spaced_rep import ReviewCard, calculate_next_review, get_due_cards, retention_rate


def test_first_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py")
    result = calculate_next_review(card, quality=4)
    assert result.interval == 1
    assert result.repetition == 1
    assert result.next_review is not None


def test_second_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=1)
    result = calculate_next_review(card, quality=4)
    assert result.interval == 6
    assert result.repetition == 2


def test_third_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=2, interval=6, ease_factor=2.5)
    result = calculate_next_review(card, quality=4)
    assert result.interval == round(6 * 2.5)  # 15
    assert result.repetition == 3


def test_fail_resets():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=5, interval=30)
    result = calculate_next_review(card, quality=1)
    assert result.repetition == 0
    assert result.interval == 1


def test_ease_factor_floor():
    card = ReviewCard(node_id="N01", cartridge_id="py", ease_factor=1.3)
    result = calculate_next_review(card, quality=0)
    assert result.ease_factor >= 1.3


def test_get_due_cards():
    now = datetime.utcnow()
    cards = [
        ReviewCard(node_id="N01", cartridge_id="py", next_review=now - timedelta(days=1)),
        ReviewCard(node_id="N02", cartridge_id="py", next_review=now + timedelta(days=1)),
        ReviewCard(node_id="N03", cartridge_id="py", next_review=now - timedelta(days=3)),
    ]
    due = get_due_cards(cards, now)
    assert len(due) == 2
    assert due[0].node_id == "N03"  # most overdue first


def test_retention_rate():
    r = retention_rate(1, 2.5)
    assert 0 < r <= 1
    assert r > 0.9  # 1天后保持率应该很高
```

### Commit

```bash
git add -A && git commit -m "feat: SM-2+ spaced repetition algorithm with review scheduling"
```

---

## 任务 4（流 B）：Assessor V2 — 策略驱动的多轮考核

**文件：**
- 创建：`starlight/core/assessor_v2.py`（新文件，不破坏旧 assessor.py）
- 创建：`tests/test_assessor_v2.py`

### assessor_v2.py

```python
# starlight/core/assessor_v2.py
"""V2 Assessor — 策略驱动的多轮考核引擎"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Awaitable


@dataclass
class AssessmentResult:
    verdict: str          # "PASS" | "FAIL" | "CONTINUE"
    feedback: str         # 给用户看的内容
    score: int            # 0-100
    hint: str | None = None
    error_type: str | None = None  # "concept" | "application" | "attention" | None
    quality: int = 3      # SM-2 quality (0-5)


class AssessorV2:
    """策略驱动的考核引擎 — 融合启智教学策略"""
    
    def __init__(self, llm_model: str, llm_api_key: str, 
                 llm_base_url: str = "", strategy=None):
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.llm_base_url = llm_base_url
        self.strategy = strategy  # TeachingStrategy instance
        self._call_llm: Callable[..., Awaitable[str]] = self._default_llm_call
    
    async def _default_llm_call(self, messages: list[dict]) -> str:
        import litellm
        kwargs = {
            "model": self.llm_model,
            "messages": messages,
            "api_key": self.llm_api_key,
        }
        if self.llm_base_url:
            kwargs["api_base"] = self.llm_base_url
        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content
    
    async def assess(self, node_content: str, pass_criteria: str,
                     session, learner) -> AssessmentResult:
        """评估用户最新回答"""
        # 构建 system prompt
        system_prompt = await self.strategy.build_system_prompt(
            node_content, pass_criteria, learner, session
        )
        
        # 获取对话上下文
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.get_context_window(max_messages=20))
        
        # 调用 LLM
        llm_response = await self._call_llm(messages)
        
        # 用策略解析结果
        passed, feedback = self.strategy.should_pass(
            llm_response, session.turn_count, session.max_turns, learner
        )
        
        # 构建结果
        if passed is True:
            score = self._estimate_score(feedback)
            quality = self._score_to_quality(score)
            return AssessmentResult(verdict="PASS", feedback=feedback, score=score, quality=quality)
        elif passed is False:
            hint = self._extract_hint(feedback)
            error_type = self._classify_error(feedback)
            return AssessmentResult(
                verdict="FAIL", feedback=feedback, score=0, 
                hint=hint, error_type=error_type, quality=1
            )
        else:
            return AssessmentResult(verdict="CONTINUE", feedback=feedback, score=0, quality=3)
    
    def _estimate_score(self, response: str) -> int:
        if any(x in response for x in ["非常好", "完全理解", "优秀", "完美"]):
            return 95
        elif any(x in response for x in ["很好", "理解", "正确", "不错"]):
            return 85
        else:
            return 75
    
    def _score_to_quality(self, score: int) -> int:
        if score >= 90: return 5
        if score >= 80: return 4
        if score >= 60: return 3
        if score >= 40: return 2
        return 1
    
    def _extract_hint(self, response: str) -> str:
        for line in response.split("\n"):
            if any(x in line for x in ["建议", "提示", "思考", "试试", "注意"]):
                return line.strip()
        return "再复习一下这个知识点，注意核心概念。"
    
    def _classify_error(self, response: str) -> str:
        if any(x in response for x in ["概念", "理解", "原理", "本质"]):
            return "concept"
        if any(x in response for x in ["应用", "场景", "实际", "例子"]):
            return "application"
        return "attention"
```

### 测试

```python
# tests/test_assessor_v2.py
import pytest
from unittest.mock import AsyncMock
from starlight.core.assessor_v2 import AssessorV2, AssessmentResult
from starlight.core.strategies import SocraticStrategy
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile


@pytest.fixture
def assessor():
    a = AssessorV2(llm_model="test", llm_api_key="test", strategy=SocraticStrategy())
    a._call_llm = AsyncMock()
    return a


@pytest.fixture
def session():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("user", "变量是存东西的")
    return s


@pytest.fixture
def learner():
    return LearnerProfile(user_id=1)


@pytest.mark.asyncio
async def test_pass(assessor, session, learner):
    assessor._call_llm.return_value = "非常好，你理解了变量赋值！[PASS]"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "PASS"
    assert result.score > 0
    assert result.quality >= 4


@pytest.mark.asyncio
async def test_fail(assessor, session, learner):
    assessor._call_llm.return_value = "还需要再想想。[FAIL] 建议：注意赋值的语法。"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "FAIL"
    assert result.hint is not None
    assert result.error_type is not None


@pytest.mark.asyncio
async def test_continue(assessor, session, learner):
    assessor._call_llm.return_value = "你能举个具体的例子吗？"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "CONTINUE"
```

### Commit

```bash
git add -A && git commit -m "feat: strategy-driven multi-turn assessor V2"
```

---

## 任务 5（流 B）：Harness V2 — 完整教学循环

**文件：**
- 创建：`starlight/core/harness_v2.py`（新文件）
- 创建：`tests/test_harness_v2.py`

### harness_v2.py

```python
# starlight/core/harness_v2.py
"""V2 Harness — 完整教学循环，融合启智教学策略"""
from __future__ import annotations
from starlight.adapters.base import HarnessResult
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile
from starlight.core.strategies import get_strategy, TeachingStrategy
from starlight.core.assessor_v2 import AssessorV2
from starlight.core.contributor import TributeEngine
from starlight.core.cartridge import CartridgeLoader
from starlight.core.spaced_rep import ReviewCard, calculate_next_review, get_due_cards


class LearningHarnessV2:
    """Starlight V2 学习引擎 — 融合启智 24 个教学 skill"""
    
    def __init__(self, cartridge_loader: CartridgeLoader,
                 assessor: AssessorV2, progress_mgr, tribute_engine: TributeEngine,
                 strategy_name: str = "adaptive"):
        self.cartridges = cartridge_loader
        self.assessor = assessor
        self.progress = progress_mgr
        self.tribute = tribute_engine
        self.strategy_name = strategy_name
        
        # 会话和画像存储（生产环境用 DB，现在用内存）
        self._sessions: dict[tuple[int, str], Session] = {}
        self._learners: dict[int, LearnerProfile] = {}
        self._review_cards: dict[int, list[ReviewCard]] = {}
    
    def get_session(self, user_id: int, cartridge_id: str) -> Session | None:
        return self._sessions.get((user_id, cartridge_id))
    
    def get_learner(self, user_id: int) -> LearnerProfile:
        if user_id not in self._learners:
            self._learners[user_id] = LearnerProfile(user_id=user_id)
        return self._learners[user_id]
    
    def _get_strategy(self) -> TeachingStrategy:
        return get_strategy(self.strategy_name)
    
    async def process(self, user_id: int, message: str, 
                      cartridge_id: str | None = None) -> HarnessResult:
        """核心方法：处理用户消息"""
        learner = self.get_learner(user_id)
        strategy = self._get_strategy()
        self.assessor.strategy = strategy
        
        # === 命令路由 ===
        if message == "/browse":
            return await self._handle_browse()
        if message == "/help":
            return self._handle_help()
        if message == "/review":
            return await self._handle_review_cards(user_id)
        if message == "/stats":
            return self._handle_stats(learner)
        if message == "/start":
            return await self._handle_start(user_id, cartridge_id, learner, strategy)
        
        # === 学习流程 ===
        if not cartridge_id:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")
        
        session = self.get_session(user_id, cartridge_id)
        if session is None:
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")
        
        # 记录用户回答
        session.add_exchange("user", message)
        
        # 加载当前节点
        cart = self.cartridges.load(cartridge_id)
        node = self.cartridges.get_node_by_id(cart, session.current_node)
        content = self.cartridges.load_node_content(cartridge_id, node["file"])
        
        # 调用 Assessor
        result = await self.assessor.assess(content, node["pass_criteria"], session, learner)
        
        # 记录 AI 回复
        session.add_exchange("assistant", result.feedback, 
                           metadata={"verdict": result.verdict, "score": result.score})
        
        # 更新学习者画像
        learner.update_from_assessment(
            score=result.score, verdict=result.verdict,
            turn_count=session.turn_count, error_type=result.error_type
        )
        
        # 处理结果
        if result.verdict == "PASS":
            return await self._handle_pass(user_id, cartridge_id, cart, node, result, session, learner)
        elif result.verdict == "FAIL":
            return self._handle_fail(result, learner)
        else:
            # CONTINUE — 继续对话
            return HarnessResult(text=f"🤔 {result.feedback}", verdict="CONTINUE", state="learning")
    
    async def _handle_start(self, user_id, cartridge_id, learner, strategy) -> HarnessResult:
        if not cartridge_id:
            return HarnessResult(text="请用 /start <卡带ID> 选择卡带。用 /browse 查看可用卡带。", state="idle")
        
        cart = self.cartridges.load(cartridge_id)
        entry = self.cartridges.get_entry_node(cart)
        content = self.cartridges.load_node_content(cartridge_id, entry["file"])
        
        # 创建会话
        session = Session(user_id=user_id, cartridge_id=cartridge_id, current_node=entry["id"])
        session.max_turns = learner.get_max_turns()
        self._sessions[(user_id, cartridge_id)] = session
        
        # 更新进度
        await self.progress.start_cartridge(user_id, cartridge_id, entry["id"])
        
        # 用策略生成开场白（不直接甩教材）
        opening = strategy.get_opening_message(entry["title"], content, learner)
        
        # 记录开场白
        session.add_exchange("system", f"知识内容：{content}")
        
        # 触发第一个问题：让 LLM 基于内容生成一个引导性问题
        first_question = await self._generate_first_question(content, entry["pass_criteria"], learner, session)
        session.add_exchange("assistant", first_question)
        
        return HarnessResult(
            text=f"{opening}\n\n{first_question}",
            state="learning",
        )
    
    async def _generate_first_question(self, content, pass_criteria, learner, session) -> str:
        """让 LLM 生成第一个引导性问题"""
        strategy = self._get_strategy()
        system_prompt = await strategy.build_system_prompt(content, pass_criteria, learner, session)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "我准备好了，请出一个场景题来考考我。"}
        ]
        
        try:
            response = await self.assessor._call_llm(messages)
            return response
        except Exception:
            return f"来看这个场景：\n\n{content}\n\n你能用自己的话解释一下这里的核心概念吗？"
    
    async def _handle_pass(self, user_id, cartridge_id, cart, node, result, session, learner) -> HarnessResult:
        next_nodes = self.cartridges.get_next_nodes(cart, node["id"])
        
        # 记录分数
        session.record_score(node["id"], result.score)
        
        # 创建复习卡片
        self._add_review_card(user_id, node["id"], cartridge_id, node.get("title", ""), result.quality)
        
        if not next_nodes:
            # 通关！
            await self.progress.complete_cartridge(user_id, cartridge_id)
            tribute_text = self.tribute.build_completion_tribute(
                cartridge_id, cart["title"], cart.get("contributors", [])
            )
            return HarnessResult(
                text=f"✅ {result.feedback}\n\n🎉 恭喜通关！\n\n{tribute_text}\n\n⚡ XP +{learner.total_xp}",
                verdict="PASS", state="completed",
            )
        else:
            # 进入下一节点
            next_node = next_nodes[0]
            await self.progress.advance_node(user_id, cartridge_id, next_node["id"])
            session.advance_node(next_node["id"])
            
            # 加载下一节点内容
            next_content = self.cartridges.load_node_content(cartridge_id, next_node["file"])
            
            # 生成下一节开场
            strategy = self._get_strategy()
            opening = strategy.get_opening_message(next_node["title"], next_content, learner)
            session.add_exchange("system", f"知识内容：{next_content}")
            
            first_q = await self._generate_first_question(next_content, next_node["pass_criteria"], learner, session)
            session.add_exchange("assistant", first_q)
            
            return HarnessResult(
                text=f"✅ {result.feedback}\n\n---\n\n{opening}\n\n{first_q}",
                verdict="PASS", state="learning", next_node=next_node["id"],
            )
    
    def _handle_fail(self, result, learner) -> HarnessResult:
        hint_text = f"\n\n💡 提示：{result.hint}" if result.hint else ""
        encouragement = ""
        if learner.confidence < 0.3:
            encouragement = "\n\n💪 别担心，学习中犯错是正常的，我们一起加油！"
        
        return HarnessResult(
            text=f"❌ {result.feedback}{hint_text}{encouragement}",
            verdict="FAIL", state="learning",
        )
    
    def _add_review_card(self, user_id, node_id, cartridge_id, title, quality):
        if user_id not in self._review_cards:
            self._review_cards[user_id] = []
        card = ReviewCard(node_id=node_id, cartridge_id=cartridge_id, title=title)
        calculate_next_review(card, quality)
        self._review_cards[user_id].append(card)
    
    async def _handle_review_cards(self, user_id) -> HarnessResult:
        cards = self._review_cards.get(user_id, [])
        due = get_due_cards(cards)
        if not due:
            return HarnessResult(text="📭 暂无需要复习的内容，继续保持学习！", state="idle")
        lines = ["📋 需要复习的内容：\n"]
        for c in due:
            lines.append(f"• {c.title} ({c.cartridge_id}/{c.node_id})")
        return HarnessResult(text="\n".join(lines), state="idle")
    
    def _handle_stats(self, learner) -> HarnessResult:
        warning = learner.get_warning()
        warning_text = f"\n\n{warning}" if warning else ""
        return HarnessResult(
            text=(
                f"📊 学习统计\n\n"
                f"⚡ XP: {learner.total_xp}\n"
                f"📚 已完成节点: {learner.nodes_completed}\n"
                f"📈 知识水平: {learner.knowledge_level:.0%}\n"
                f"🎯 自信度: {learner.confidence:.0%}\n"
                f"🧠 布鲁姆层次: L{learner.bloom_level}\n"
                f"🔥 连续学习: {learner.streak_days} 天"
                f"{warning_text}"
            ),
            state="idle",
        )
    
    # 复用 V1 的 browse/help
    async def _handle_browse(self) -> HarnessResult:
        cartridges = self.cartridges.list_cartridges()
        lines = ["📚 可用卡带：\n"]
        for cart_id in cartridges:
            try:
                cart = self.cartridges.load(cart_id)
                lines.append(f"• {cart['title']} ({cart_id}) — {len(cart['nodes'])} 个知识点")
            except Exception:
                lines.append(f"• {cart_id}")
        lines.append("\n用 /start <卡带ID> 开始学习")
        return HarnessResult(text="\n".join(lines), state="idle")
    
    def _handle_help(self) -> HarnessResult:
        return HarnessResult(
            text=(
                "🌟 星光学习机 V2\n\n"
                "指令：\n"
                "/browse — 浏览卡带\n"
                "/start <ID> — 开始学习\n"
                "/stats — 学习统计\n"
                "/review — 复习到期内容\n"
                "/help — 帮助\n\n"
                "💡 直接输入文字 = 回答考核问题\n"
                "系统会根据你的水平自动调整教学策略"
            ),
            state="idle",
        )
```

### 测试

```python
# tests/test_harness_v2.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.harness_v2 import LearningHarnessV2
from starlight.core.assessor_v2 import AssessorV2
from starlight.core.strategies import SocraticStrategy
from starlight.core.contributor import TributeEngine
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile
from starlight.main import MockProgressManager


@pytest.fixture
def harness():
    loader = MagicMock()
    loader.list_cartridges.return_value = ["python-basics"]
    loader.load.return_value = {
        "id": "python-basics", "title": "Python",
        "nodes": [
            {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"},
            {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
        ],
        "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": []}},
    }
    loader.get_entry_node.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    loader.get_next_nodes.return_value = [{"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"}]
    loader.get_node_by_id.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    
    assessor = AssessorV2(llm_model="test", llm_api_key="test", strategy=SocraticStrategy())
    assessor._call_llm = AsyncMock()
    
    progress = MockProgressManager()
    tribute = TributeEngine()
    
    return LearningHarnessV2(loader, assessor, progress, tribute, strategy_name="socratic")


@pytest.mark.asyncio
async def test_start_creates_session(harness):
    harness.assessor._call_llm.return_value = "来考考你：什么是变量？"
    result = await harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    assert result.state == "learning"
    session = harness.get_session(1, "python-basics")
    assert session is not None
    assert session.current_node == "N01"


@pytest.mark.asyncio
async def test_full_flow(harness):
    # Start
    harness.assessor._call_llm.return_value = "来考考你：什么是变量？"
    await harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    
    # Answer — LLM returns PASS
    harness.assessor._call_llm.return_value = "非常好！[PASS]"
    harness.cartridges.get_node_by_id.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    result = await harness.process(user_id=1, message="变量就是存数据的盒子", cartridge_id="python-basics")
    assert result.verdict == "PASS"
    
    # Check learner profile updated
    learner = harness.get_learner(1)
    assert learner.total_xp > 0
    assert learner.nodes_completed == 1


@pytest.mark.asyncio
async def test_continue_flow(harness):
    harness.assessor._call_llm.return_value = "来考考你"
    await harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    
    harness.assessor._call_llm.return_value = "你能更具体地说明吗？"
    harness.cartridges.get_node_by_id.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    result = await harness.process(user_id=1, message="存东西的", cartridge_id="python-basics")
    assert result.verdict == "CONTINUE"
    
    # Session has conversation history
    session = harness.get_session(1, "python-basics")
    assert len(session.conversation) >= 3


@pytest.mark.asyncio
async def test_stats(harness):
    result = await harness.process(user_id=1, message="/stats")
    assert "XP" in result.text
    assert "知识水平" in result.text
```

### Commit

```bash
git add -A && git commit -m "feat: Harness V2 with full teaching loop, learner profiles, and review cards"
```

---

## 任务 6（流 C）：Telegram Adapter V2 + run_bot.py 更新

**文件：**
- 修改：`starlight/adapters/telegram_adapter.py` — 支持 V2 Harness
- 修改：`run_bot.py` — 切换到 V2

### telegram_adapter.py 修改要点

```python
# 主要改动：
# 1. harness_factory 返回 LearningHarnessV2 实例
# 2. 新增 /stats 和 /review 命令处理
# 3. 消息路由适配 V2 的返回格式
```

### run_bot.py 修改要点

```python
# 主要改动：
# 1. 导入 AssessorV2 和 LearningHarnessV2
# 2. 创建 AssessorV2 时传入 llm_base_url
# 3. 设置 strategy_name="adaptive"
```

### Commit

```bash
git add -A && git commit -m "feat: Telegram adapter V2 with stats, review, and adaptive strategy"
```

---

## 自审

### 规格覆盖

| 设计文档需求 | 对应 Task | 状态 |
|-------------|----------|------|
| 苏格拉底对话策略 | Task 2 | ✅ |
| 认知负荷控制 | Task 1 (LearnerProfile) | ✅ |
| 自适应难度调整 | Task 2 (AdaptiveStrategy) | ✅ |
| 学习者画像 + ZPD | Task 1 (LearnerProfile) | ✅ |
| 间隔重复 SM-2 | Task 3 | ✅ |
| 游戏化 XP | Task 1 (LearnerProfile) | ✅ |
| 错误模式分析 | Task 1 (LearnerProfile) | ✅ |
| 多轮对话记忆 | Task 1 (Session) | ✅ |
| 引导式提问（不甩教材） | Task 5 (_generate_first_question) | ✅ |
| 费曼技巧 | Task 2 (FeynmanStrategy) | ✅ |
| 脚手架教学 | Task 2 (ScaffoldStrategy) | ✅ |
| Agent Loop 模式 | Task 5 (HarnessV2.process) | ✅ |
| OpenHarness Skills 思路 | Task 2 (可插拔策略) | ✅ |
| OpenHarness Memory 思路 | Task 1 (Session + Learner) | ✅ |
| LLM base_url 配置 | Task 4 (AssessorV2) | ✅ |
| 动机预警 | Task 1 (LearnerProfile.get_warning) | ✅ |

### 占位符扫描：无 TODO/TBD ✅

### 类型一致性：
- `AssessmentResult` 在 assessor_v2.py 中新定义，不影响旧版
- `HarnessResult` 在 base.py 不变，V1 V2 都用
- `Session` 和 `LearnerProfile` 在 harness_v2.py 中正确引用 ✅

### 并行安全性：
- **流 A**（Task 1-3）：全部新建文件，不改现有代码
- **流 B**（Task 4-5）：全部新建文件（assessor_v2.py, harness_v2.py），不改旧文件
- **流 C**（Task 6）：修改 telegram_adapter.py 和 run_bot.py，但不和 A/B 冲突
- 三条流互不干扰 ✅

### 缺口：无 ✅

---

**计划保存到：** `docs/superpowers/plans/2026-04-04-starlight-engine-v2.md`

**并行执行方案：**
- **Agent A**：Task 1 → Task 2 → Task 3（Session + Learner + Strategies + Spaced Rep，串行）
- **Agent B**：Task 4 → Task 5（Assessor V2 + Harness V2，串行）
- **Agent C**：Task 6（Telegram Adapter V2 + run_bot.py 更新）

等 Task 4-5 完成后再 dispatch Task 6（因为需要依赖 V2 的接口）。

实际上流 C 依赖流 B 的结果，所以先并行跑 A + B，完成后再跑 C。
