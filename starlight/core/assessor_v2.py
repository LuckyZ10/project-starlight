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
    
    async def _default_llm_call(self, messages: list[dict]) -> tuple[str, str]:
        """Call LLM. Returns (system_prompt, response_text).

        We return system_prompt so assess() can reuse it.
        """
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url or "https://open.bigmodel.cn/api/anthropic",
        )
        # Split system messages from user/assistant messages
        system_parts = []
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                chat_messages.append(msg)
        
        # Ensure at least one user message exists
        if not chat_messages:
            chat_messages = [{"role": "user", "content": "开始"}]
        
        system_text = "\n\n".join(system_parts) if system_parts else None
        
        kwargs = {
            "model": self.llm_model,
            "max_tokens": 1024,
            "messages": chat_messages,
        }
        if system_text:
            kwargs["system"] = system_text
        
        response = await client.messages.create(**kwargs)
        return response.content[0].text
    
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
