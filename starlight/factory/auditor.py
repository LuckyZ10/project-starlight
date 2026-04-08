# starlight/factory/auditor.py
"""Phase 3: 覆盖率审计 — 确保每个知识点都被节点内容覆盖"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from starlight.factory.extractor import KnowledgePoint, ExtractionResult
from starlight.factory.builder import NodeSpec, BuildResult
from starlight.factory.prompts import AUDIT_SYSTEM, AUDIT_USER

logger = logging.getLogger(__name__)


@dataclass
class CoverageDetail:
    kp_id: str
    status: str       # FULL | PARTIAL | MISSING | DISTORTED
    mapped_node: str
    issue: str = ""


@dataclass
class CoverageReport:
    total: int
    full: int
    partial: int
    missing: int
    distorted: int
    coverage_percent: float
    details: list[CoverageDetail] = field(default_factory=list)

    @property
    def is_passing(self) -> bool:
        return self.coverage_percent >= 99.0

    @property
    def gap_kp_ids(self) -> list[str]:
        """需要补漏的知识点 ID"""
        return [
            d.kp_id for d in self.details
            if d.status in ("MISSING", "PARTIAL", "DISTORTED")
        ]


class CoverageAuditor:
    """Phase 3: 审计知识点覆盖率"""

    def __init__(self, llm_call_fn):
        self._call_llm = llm_call_fn

    async def audit(self, extraction: ExtractionResult, build: BuildResult) -> CoverageReport:
        """执行覆盖率审计"""
        kps_json = json.dumps(
            [
                {"id": kp.id, "statement": kp.statement, "type": kp.type}
                for kp in extraction.knowledge_points
            ],
            ensure_ascii=False,
            indent=2,
        )

        nodes_content = "\n\n".join(
            f"=== {node.id}: {node.title} ===\n{node.content[:2000]}"
            for node in build.nodes
        )

        user_prompt = AUDIT_USER.format(
            total_kps=extraction.total,
            kps_json=kps_json,
            nodes_content=nodes_content,
        )

        messages = [
            {"role": "system", "content": AUDIT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("Phase 3: auditing coverage of %d KPs...", extraction.total)

        # 重试逻辑（API 偶发 500）
        for attempt in range(5):
            try:
                response = await self._call_llm(messages)
                break
            except Exception as e:
                if attempt < 4:
                    wait = [10, 20, 30, 40][attempt]
                    logger.warning("Phase 3: API error (attempt %d), retrying in %ds: %s", attempt + 1, wait, e)
                    import asyncio
                    await asyncio.sleep(wait)
                else:
                    raise

        return self._parse_audit_response(response, extraction.total)

    def _parse_audit_response(self, response: str, total: int) -> CoverageReport:
        """解析审计结果"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Phase 3: JSON parse failed")
            return CoverageReport(total=total, full=0, partial=0, missing=total,
                                  distorted=0, coverage_percent=0.0)

        report_data = data.get("coverage_report", {})
        details = []
        for d in data.get("details", []):
            details.append(CoverageDetail(
                kp_id=d.get("kp_id", ""),
                status=d.get("status", "MISSING"),
                mapped_node=d.get("mapped_node", ""),
                issue=d.get("issue", ""),
            ))

        coverage = report_data.get("coverage_percent", 0)
        if isinstance(coverage, str):
            coverage = float(coverage.replace("%", ""))

        report = CoverageReport(
            total=report_data.get("total", total),
            full=report_data.get("full", 0),
            partial=report_data.get("partial", 0),
            missing=report_data.get("missing", 0),
            distorted=report_data.get("distorted", 0),
            coverage_percent=coverage,
            details=details,
        )

        logger.info(
            "Phase 3: coverage %.1f%% (%d full, %d partial, %d missing, %d distorted)",
            report.coverage_percent, report.full, report.partial,
            report.missing, report.distorted,
        )
        return report
