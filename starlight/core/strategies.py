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

    def get_opening_message(self, node_title: str, node_content: str,
                            learner: Any) -> str:
        """生成开场白（不直接甩教材）"""
        return (
            f"📚 今天我们来学习「{node_title}」\n\n"
            f"我准备了一个场景来考考你，准备好了吗？直接回答就好！"
        )


class SocraticStrategy(TeachingStrategy):
    """苏格拉底策略 — 通过提问引导学习者自己发现答案"""

    name = "socratic"
    description = "苏格拉底式提问引导"

    async def build_system_prompt(self, node_content, pass_criteria,
                                  learner, session):
        learner_desc = self._describe_learner(learner)
        force_hint = ""
        if session.should_force_verdict():
            force_hint = (
                "\n\n⚠️ 这是最后一轮了，你必须做出判定：[PASS] 或 [FAIL]。"
            )

        difficulty_hint = ""
        mod = learner.get_difficulty_modifier() if learner else 1.0
        if mod < 1.0:
            difficulty_hint = (
                "\n难度调整：学习者基础较弱，用更简单的场景和更多提示。"
            )
        elif mod > 1.0:
            difficulty_hint = "\n难度调整：学习者水平较高，用更有挑战的场景。"

        hint_instruction = ""
        if learner and learner.should_get_hint():
            hint_instruction = (
                "\n注意：学习者当前认知负荷较高，在追问时给出明确的方向性提示。"
            )

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
        zpd = {
            "below": "偏低（内容偏简单）",
            "zpd": "恰好（最佳学习区）",
            "above": "偏高（需要更多帮助）",
        }
        return (
            f"知识水平：{learner.knowledge_level:.0%} | "
            f"自信度：{learner.confidence:.0%} | "
            f"布鲁姆层次：L{learner.bloom_level} | "
            f"ZPD：{zpd.get(learner.zpd_zone.value, '未知')}"
        )


class FeynmanStrategy(TeachingStrategy):
    """费曼技巧策略 — 让学习者"教"来检验理解"""

    name = "feynman"
    description = "费曼技巧 — 用教来学"

    async def build_system_prompt(self, node_content, pass_criteria,
                                  learner, session):
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
            f"我来考考你：假设你要把这个概念教给一个 12 岁的孩子，"
            f"你会怎么解释？"
        )


class ScaffoldStrategy(TeachingStrategy):
    """脚手架策略 — 分步骤逐步引导"""

    name = "scaffold"
    description = "脚手架教学 — 分步引导"

    async def build_system_prompt(self, node_content, pass_criteria,
                                  learner, session):
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
    """自适应策略 — 根据学习者画像动态选择策略"""

    name = "adaptive"
    description = "自适应混合策略"

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

    async def build_system_prompt(self, node_content, pass_criteria,
                                  learner, session):
        strategy = self._select_strategy(learner)
        return await strategy.build_system_prompt(
            node_content, pass_criteria, learner, session
        )

    def should_pass(self, llm_response, turn_count, max_turns, learner):
        strategy = self._select_strategy(learner)
        return strategy.should_pass(
            llm_response, turn_count, max_turns, learner
        )

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
