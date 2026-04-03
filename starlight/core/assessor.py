from dataclasses import dataclass
from typing import Callable, Awaitable

@dataclass
class AssessmentResult:
    verdict: str  # "PASS", "FAIL", "CONTINUE"
    feedback: str
    score: int  # 0-100
    hint: str | None = None

class Assessor:
    def __init__(self, llm_model: str, llm_api_key: str, max_turns: int = 3):
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.max_turns = max_turns
        self._call_llm: Callable[..., Awaitable[str]] = self._default_llm_call

    async def _default_llm_call(self, messages: list[dict]) -> str:
        """实际 LLM 调用（通过 litellm）。测试时会被 mock 替换。"""
        import litellm
        response = await litellm.acompletion(
            model=self.llm_model,
            messages=messages,
            api_key=self.llm_api_key,
        )
        return response.choices[0].message.content

    async def assess(
        self,
        node_content: str,
        pass_criteria: str,
        conversation: list[dict],
        user_answer: str,
    ) -> AssessmentResult:
        """评估用户回答，返回 PASS/FAIL/CONTINUE。"""
        system_prompt = self._build_system_prompt(node_content, pass_criteria, self.max_turns)
        messages = (
            [{"role": "system", "content": system_prompt}]
            + conversation
            + [{"role": "user", "content": user_answer}]
        )
        llm_response = await self._call_llm(messages)
        return self._parse_response(llm_response)

    def _build_system_prompt(self, node_content: str, pass_criteria: str, max_turns: int) -> str:
        return f"""你是星光学习机的考核官。

考核规则：
1. 基于以下知识内容考核学习者
2. 不要直接问教材里有的问题，创设真实场景让学习者应用知识
3. 学习者回答后，判断是否真正理解
4. 判定通过时输出 [PASS]，判定不通过时输出 [FAIL] 并给出提示
5. 如果回答模糊，继续追问（最多{max_turns}轮），然后必须判定
6. 绝不直接告诉答案，只给方向性提示

知识内容：
{node_content}

通过标准：
{pass_criteria}"""

    def _parse_response(self, response: str) -> AssessmentResult:
        """解析 LLM 输出，提取判定、分数、提示。"""
        upper = response.upper()
        if "[PASS]" in upper:
            score = self._estimate_score(response)
            return AssessmentResult(verdict="PASS", feedback=response, score=score)
        elif "[FAIL]" in upper:
            hint = self._extract_hint(response)
            return AssessmentResult(verdict="FAIL", feedback=response, score=0, hint=hint)
        else:
            return AssessmentResult(verdict="CONTINUE", feedback=response, score=0)

    def _estimate_score(self, response: str) -> int:
        """根据 LLM 反馈估算分数（启发式）。"""
        if "非常好" in response or "完全理解" in response or "优秀" in response:
            return 95
        elif "很好" in response or "理解" in response or "正确" in response:
            return 85
        else:
            return 70

    def _extract_hint(self, response: str) -> str:
        """从 FAIL 回复中提取提示。"""
        lines = response.split("\n")
        for line in lines:
            if "建议" in line or "提示" in line or "思考" in line:
                return line.strip()
        return "再复习一下这个知识点，注意核心概念。"
