# starlight/factory/builder.py
"""Phase 2: 知识点分组 + DAG 构建 + 节点内容生成"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from starlight.factory.extractor import KnowledgePoint, ExtractionResult
from starlight.factory.prompts import BUILD_SYSTEM, BUILD_USER, NODE_CONTENT_SYSTEM, NODE_CONTENT_USER

logger = logging.getLogger(__name__)


@dataclass
class NodeSpec:
    id: str
    title: str
    kp_ids: list[str]
    prerequisites: list[str]
    difficulty: int
    pass_criteria: str
    summary: str
    content: str = ""  # 生成的 Markdown 内容


@dataclass
class BuildResult:
    nodes: list[NodeSpec]
    dag_entry: str
    dag_edges: dict[str, list[str]]

    def to_manifest(self, cartridge_id: str, title: str, version: str = "1.0.0",
                    language: str = "zh-CN") -> dict:
        """生成 manifest.json 格式"""
        return {
            "id": cartridge_id,
            "title": title,
            "version": version,
            "language": language,
            "contributors": [
                {"name": "Cartridge Factory", "role": "auto-generated", "quote": "由教材制造机自动生成"}
            ],
            "nodes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "file": f"nodes/{n.id}-{self._slugify(n.title)}.md",
                    "prerequisites": n.prerequisites,
                    "difficulty": n.difficulty,
                    "pass_criteria": n.pass_criteria,
                }
                for n in self.nodes
            ],
            "dag": {
                "entry": self.dag_entry,
                "edges": self.dag_edges,
            },
        }

    @staticmethod
    def _slugify(title: str) -> str:
        """标题转文件名友好格式"""
        # 简单处理：移除特殊字符，空格变横线
        slug = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', title)
        slug = re.sub(r'[\s]+', '-', slug).strip('-')
        return slug[:50] if slug else "untitled"


class NodeBuilder:
    """Phase 2: 将知识点分组为节点并构建 DAG"""

    def __init__(self, llm_call_fn, source_content: str = ""):
        self._call_llm = llm_call_fn
        self.source_content = source_content

    async def build(self, extraction: ExtractionResult) -> BuildResult:
        """从提取结果构建节点和 DAG"""
        kps_json = json.dumps(
            [
                {
                    "id": kp.id,
                    "type": kp.type,
                    "statement": kp.statement,
                    "source_section": kp.source_section,
                    "keywords": kp.keywords,
                }
                for kp in extraction.knowledge_points
            ],
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = BUILD_USER.format(
            total_kps=extraction.total,
            kps_json=kps_json,
        )

        messages = [
            {"role": "system", "content": BUILD_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("Phase 2: building nodes and DAG from %d KPs...", extraction.total)
        response = await self._call_llm(messages)
        build_data = self._parse_build_response(response)

        # 构建 NodeSpec 列表（暂无内容）
        node_map: dict[str, NodeSpec] = {}
        for node_data in build_data.get("nodes", []):
            node_map[node_data["id"]] = NodeSpec(
                id=node_data["id"],
                title=node_data["title"],
                kp_ids=node_data.get("kp_ids", []),
                prerequisites=node_data.get("prerequisites", []),
                difficulty=node_data.get("difficulty", 2),
                pass_criteria=node_data.get("pass_criteria", ""),
                summary=node_data.get("summary", ""),
            )

        dag = build_data.get("dag", {})
        entry = dag.get("entry", "")
        edges = dag.get("edges", {})

        # Phase 2.5: 生成每个节点的内容
        kp_by_id = {kp.id: kp for kp in extraction.knowledge_points}
        for node_id, node_spec in node_map.items():
            logger.info("Phase 2.5: generating content for %s (%s)...", node_id, node_spec.title)
            content = await self._generate_node_content(node_spec, kp_by_id)
            node_spec.content = content

        return BuildResult(
            nodes=list(node_map.values()),
            dag_entry=entry,
            dag_edges=edges,
        )

    async def _generate_node_content(self, node: NodeSpec,
                                      kp_by_id: dict[str, KnowledgePoint]) -> str:
        """为单个节点生成教学内容"""
        kps_detail = "\n".join(
            f"- [{kp_by_id[kpid].type}] {kp_by_id[kpid].statement}"
            for kpid in node.kp_ids
            if kpid in kp_by_id
        )

        # 从原文中找到相关片段
        source_parts = []
        for kpid in node.kp_ids:
            if kpid in kp_by_id and kp_by_id[kpid].source_text:
                source_parts.append(kp_by_id[kpid].source_text)
        source_material = "\n---\n".join(source_parts) if source_parts else self.source_content[:3000]

        user_prompt = NODE_CONTENT_USER.format(
            node_title=node.title,
            pass_criteria=node.pass_criteria,
            difficulty=node.difficulty,
            kp_count=len(node.kp_ids),
            kps_detail=kps_detail,
            source_material=source_material,
        )

        messages = [
            {"role": "system", "content": NODE_CONTENT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        return await self._call_llm(messages)

    def _parse_build_response(self, response: str) -> dict:
        """解析 LLM 返回的构建结果"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Phase 2: JSON parse failed, attempting recovery")
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error("Phase 2: JSON recovery failed")
                return {"nodes": [], "dag": {"entry": "", "edges": {}}}
