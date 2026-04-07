# starlight/factory/validator.py
"""Phase 4: 多视角交叉验证"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from starlight.factory.extractor import ExtractionResult
from starlight.factory.builder import BuildResult
from starlight.factory.prompts import (
    VALIDATE_LEARNER_SYSTEM, VALIDATE_EXPERT_SYSTEM,
    VALIDATE_ASSESSMENT_SYSTEM, VALIDATE_DAG_SYSTEM,
    VALIDATE_USER,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    severity: str      # critical | warning | suggestion
    category: str      # jump | accuracy | assessment | structure | other
    location: str      # 涉及的节点或知识点
    description: str
    suggestion: str


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)
    summary: str = ""

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def is_passing(self) -> bool:
        return self.critical_count == 0


class CrossValidator:
    """Phase 4: 从 4 个视角交叉验证课程质量"""

    def __init__(self, llm_call_fn):
        self._call_llm = llm_call_fn

    async def validate(self, title: str, extraction: ExtractionResult,
                       build: BuildResult) -> ValidationResult:
        """执行 4 视角验证"""
        # 准备通用上下文
        context = self._build_context(title, extraction, build)

        all_issues: list[ValidationIssue] = []

        perspectives = [
            ("学习者视角", VALIDATE_LEARNER_SYSTEM),
            ("专家视角", VALIDATE_EXPERT_SYSTEM),
            ("考核视角", VALIDATE_ASSESSMENT_SYSTEM),
            ("结构视角", VALIDATE_DAG_SYSTEM),
        ]

        for name, system_prompt in perspectives:
            logger.info("Phase 4: running %s validation...", name)
            try:
                response = await self._run_perspective(system_prompt, context)
                issues = self._parse_issues(response, name)
                all_issues.extend(issues)
            except Exception as e:
                logger.warning("Phase 4: %s validation failed: %s", name, e)

        # 汇总
        critical = sum(1 for i in all_issues if i.severity == "critical")
        warnings = sum(1 for i in all_issues if i.severity == "warning")
        summary = f"共发现 {len(all_issues)} 个问题（{critical} critical, {warnings} warning）"

        logger.info("Phase 4: %s", summary)

        return ValidationResult(issues=all_issues, summary=summary)

    def _build_context(self, title: str, extraction: ExtractionResult,
                       build: BuildResult) -> str:
        """构建验证用的通用上下文"""
        nodes_json = json.dumps(
            [
                {
                    "id": n.id,
                    "title": n.title,
                    "difficulty": n.difficulty,
                    "pass_criteria": n.pass_criteria,
                    "prerequisites": n.prerequisites,
                    "kp_ids": n.kp_ids,
                }
                for n in build.nodes
            ],
            ensure_ascii=False,
            indent=2,
        )

        dag_json = json.dumps(build.dag_edges, ensure_ascii=False, indent=2)

        nodes_summary = "\n".join(
            f"[{n.id} {n.title}] {n.content[:200]}..."
            for n in build.nodes
        )

        return VALIDATE_USER.format(
            title=title,
            node_count=len(build.nodes),
            kp_count=extraction.total,
            nodes_json=nodes_json,
            dag_json=dag_json,
            nodes_summary=nodes_summary,
        )

    async def _run_perspective(self, system_prompt: str, context: str) -> str:
        """运行单个视角的验证"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]
        return await self._call_llm(messages)

    def _parse_issues(self, response: str, perspective: str) -> list[ValidationIssue]:
        """解析验证结果"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Phase 4 [%s]: JSON parse failed", perspective)
            return []

        issues = []
        for item in data.get("issues", []):
            issues.append(ValidationIssue(
                severity=item.get("severity", "warning"),
                category=item.get("category", "other"),
                location=item.get("location", ""),
                description=f"[{perspective}] {item.get('description', '')}",
                suggestion=item.get("suggestion", ""),
            ))

        return issues
