# starlight/factory/pipeline.py
"""Cartridge Factory 主流水线 — 5 阶段编排"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from starlight.factory.extractor import KnowledgeExtractor, ExtractionResult
from starlight.factory.builder import NodeBuilder, BuildResult
from starlight.factory.auditor import CoverageAuditor, CoverageReport
from starlight.factory.validator import CrossValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class FactoryOutput:
    """工厂最终输出"""
    cartridge_id: str
    cartridge_dir: str          # 输出目录路径
    manifest_path: str          # manifest.json 路径
    total_kps: int              # 总知识点数
    total_nodes: int            # 总节点数
    coverage: float             # 覆盖率 %
    validation: ValidationResult  # 验证结果
    coverage_report: CoverageReport | None = None

    def summary(self) -> str:
        lines = [
            f"✅ 卡带制造完成：{self.cartridge_id}",
            f"📊 知识点：{self.total_kps} 个 → 节点：{self.total_nodes} 个",
            f"📈 覆盖率：{self.coverage:.1f}%",
            f"🔍 验证：{self.validation.summary}",
        ]
        if self.validation.issues:
            critical = [i for i in self.validation.issues if i.severity == "critical"]
            if critical:
                lines.append(f"⚠️ Critical issues ({len(critical)}):")
                for issue in critical[:5]:
                    lines.append(f"  - {issue.description[:80]}")
        return "\n".join(lines)


class CartridgeFactory:
    """教材制造机 — 原始文档 → .star 卡带

    使用方式：
        factory = CartridgeFactory(llm_call_fn=my_llm)
        result = await factory.manufacture(
            title="Transformer 完全指南",
            content=open("transformer.md").read(),
            cartridge_id="transformer-complete",
            output_dir="./cartridges",
        )
    """

    def __init__(self, llm_call_fn, *,
                 coverage_threshold: float = 99.0,
                 max_audit_rounds: int = 3):
        """
        Args:
            llm_call_fn: async callable(messages: list[dict]) -> str
            coverage_threshold: 覆盖率达标线（默认 99%）
            max_audit_rounds: 最大审计补漏轮数（默认 3 轮）
        """
        self.extractor = KnowledgeExtractor(llm_call_fn)
        self.builder = NodeBuilder(llm_call_fn)
        self.auditor = CoverageAuditor(llm_call_fn)
        self.validator = CrossValidator(llm_call_fn)
        self.coverage_threshold = coverage_threshold
        self.max_audit_rounds = max_audit_rounds

    async def manufacture(
        self,
        title: str,
        content: str,
        cartridge_id: str,
        output_dir: str = "./cartridges",
        contributor: dict | None = None,
    ) -> FactoryOutput:
        """执行完整的 5 阶段制造流程

        Args:
            title: 课程标题
            content: 原始 Markdown 内容
            cartridge_id: 卡带唯一 ID（用于目录名）
            output_dir: 输出根目录
            contributor: 贡献者信息（可选）

        Returns:
            FactoryOutput 包含路径和统计信息
        """
        logger.info("=" * 60)
        logger.info("Cartridge Factory: manufacturing '%s'", cartridge_id)
        logger.info("Input: %d chars", len(content))
        logger.info("=" * 60)

        # ================================================================
        # Phase 1: 知识点原子提取
        # ================================================================
        logger.info("▶ Phase 1: EXTRACT — extracting knowledge points...")
        extraction = await self.extractor.extract(title, content)
        logger.info("  → Extracted %d knowledge points", extraction.total)

        # ================================================================
        # Phase 2: 分组 + DAG + 内容生成
        # ================================================================
        logger.info("▶ Phase 2: BUILD — building nodes and DAG...")
        self.builder.source_content = content  # 传原文给内容生成
        build = await self.builder.build(extraction)
        logger.info("  → Built %d nodes, DAG entry: %s", len(build.nodes), build.dag_entry)

        # ================================================================
        # Phase 3: 覆盖率审计（循环补漏）
        # ================================================================
        logger.info("▶ Phase 3: AUDIT — checking coverage...")
        coverage_report = await self._audit_loop(extraction, build)
        logger.info("  → Final coverage: %.1f%%", coverage_report.coverage_percent)

        # ================================================================
        # Phase 4: 多视角交叉验证
        # ================================================================
        logger.info("▶ Phase 4: VALIDATE — cross-validating...")
        validation = await self.validator.validate(title, extraction, build)
        logger.info("  → %s", validation.summary)

        # ================================================================
        # Phase 5: 打包输出
        # ================================================================
        logger.info("▶ Phase 5: PACKAGE — writing .star cartridge...")
        manifest = build.to_manifest(cartridge_id, title)

        if contributor:
            manifest["contributors"] = [contributor]

        cartridge_dir = await self._write_cartridge(
            output_dir, cartridge_id, manifest, build
        )

        logger.info("✅ Cartridge '%s' manufactured at %s", cartridge_id, cartridge_dir)

        return FactoryOutput(
            cartridge_id=cartridge_id,
            cartridge_dir=cartridge_dir,
            manifest_path=os.path.join(cartridge_dir, "manifest.json"),
            total_kps=extraction.total,
            total_nodes=len(build.nodes),
            coverage=coverage_report.coverage_percent,
            validation=validation,
            coverage_report=coverage_report,
        )

    async def _audit_loop(self, extraction: ExtractionResult,
                          build: BuildResult) -> CoverageReport:
        """覆盖率审计循环：不达标就补漏，最多 max_audit_rounds 轮"""
        report = await self.auditor.audit(extraction, build)

        round_num = 1
        while report.coverage_percent < self.coverage_threshold and round_num < self.max_audit_rounds:
            gap_ids = report.gap_kp_ids
            logger.info(
                "  Round %d: coverage %.1f%% < %.1f%%, patching %d gaps...",
                round_num, report.coverage_percent, self.coverage_threshold, len(gap_ids),
            )

            # 找到缺失的知识点
            gap_kps = [kp for kp in extraction.knowledge_points if kp.id in gap_ids]

            # 补入最相关的节点（按 source_section 匹配）
            for kp in gap_kps:
                best_node = self._find_best_node(kp, build.nodes)
                if best_node:
                    # 追加到节点内容末尾
                    best_node.content += f"\n\n## 补充：{kp.statement}\n\n{kp.source_text}"
                    if kp.id not in best_node.kp_ids:
                        best_node.kp_ids.append(kp.id)

            # 重新审计
            report = await self.auditor.audit(extraction, build)
            round_num += 1

        return report

    def _find_best_node(self, kp, nodes: list) -> object | None:
        """为缺失知识点找到最匹配的节点"""
        # 优先按 source_section 匹配
        best_node = None
        best_score = -1

        for node in nodes:
            score = 0
            # 标题关键词匹配
            for kw in kp.keywords:
                if kw in node.title:
                    score += 2
            # 内容中已有相关关键词
            for kw in kp.keywords:
                if kw in node.content:
                    score += 1
            if score > best_score:
                best_score = score
                best_node = node

        return best_node

    async def _write_cartridge(self, output_dir: str, cartridge_id: str,
                                manifest: dict, build: BuildResult) -> str:
        """写入 .star 卡带文件"""
        cart_dir = Path(output_dir) / cartridge_id
        nodes_dir = cart_dir / "nodes"
        nodes_dir.mkdir(parents=True, exist_ok=True)

        # 写 manifest.json
        manifest_path = cart_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 写节点 .md 文件
        for node in build.nodes:
            filename = manifest["nodes"][
                next(i for i, n in enumerate(manifest["nodes"]) if n["id"] == node.id)
            ]["file"]
            node_path = cart_dir / filename
            node_path.parent.mkdir(parents=True, exist_ok=True)
            node_path.write_text(node.content, encoding="utf-8")

        return str(cart_dir)
