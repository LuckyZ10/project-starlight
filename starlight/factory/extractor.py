# starlight/factory/extractor.py
"""Phase 1: 知识点原子提取 — 从原始 MD 提取不可再分的知识点"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from starlight.factory.prompts import EXTRACT_SYSTEM, EXTRACT_USER, EXTRACT_CHUNK_USER

logger = logging.getLogger(__name__)


@dataclass
class KnowledgePoint:
    id: str                    # KP-001
    type: str                  # fact|concept|formula|procedure|example
    statement: str             # 完整描述
    source_section: str        # 原文章节位置
    source_text: str           # 原文片段
    keywords: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    title: str
    knowledge_points: list[KnowledgePoint]

    @property
    def total(self) -> int:
        return len(self.knowledge_points)

    def to_json(self) -> str:
        data = {
            "title": self.title,
            "total_kps": self.total,
            "knowledge_points": [
                {
                    "id": kp.id,
                    "type": kp.type,
                    "statement": kp.statement,
                    "source_section": kp.source_section,
                    "source_text": kp.source_text,
                    "keywords": kp.keywords,
                }
                for kp in self.knowledge_points
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


class KnowledgeExtractor:
    """Phase 1: 从原始文档中提取知识点原子"""

    def __init__(self, llm_call_fn, chunk_max_chars: int = 12000):
        """
        Args:
            llm_call_fn: async callable(messages) -> str
            chunk_max_chars: 每个分块的最大字符数（避免上下文溢出）
        """
        self._call_llm = llm_call_fn
        self.chunk_max_chars = chunk_max_chars

    def _chunk_text(self, text: str) -> list[str]:
        """按章节/段落分块，尽量在标题处切割"""
        # 按二级标题切割
        sections = re.split(r'\n(?=#{1,3}\s)', text)

        chunks: list[str] = []
        current = ""

        for section in sections:
            if not section.strip():
                continue
            if len(current) + len(section) > self.chunk_max_chars and current:
                chunks.append(current)
                current = section
            else:
                current += "\n" + section if current else section

        if current.strip():
            chunks.append(current)

        # 如果只有一个超大块，强制按段落切
        if len(chunks) == 1 and len(chunks[0]) > self.chunk_max_chars:
            paragraphs = chunks[0].split("\n\n")
            chunks = []
            current = ""
            for p in paragraphs:
                if len(current) + len(p) > self.chunk_max_chars and current:
                    chunks.append(current)
                    current = p
                else:
                    current += "\n\n" + p if current else p
            if current.strip():
                chunks.append(current)

        return chunks

    async def extract(self, title: str, content: str) -> ExtractionResult:
        """从文档中提取所有知识点原子"""
        chunks = self._chunk_text(content)
        logger.info("Phase 1: splitting into %d chunks (total %d chars)", len(chunks), len(content))

        all_kps: list[KnowledgePoint] = []
        kp_counter = 0

        for i, chunk in enumerate(chunks):
            logger.info("Phase 1: extracting chunk %d/%d", i + 1, len(chunks))

            if len(chunks) == 1:
                user_prompt = EXTRACT_USER.format(title=title, content=chunk)
            else:
                user_prompt = EXTRACT_CHUNK_USER.format(
                    chunk_index=i + 1,
                    total_chunks=len(chunks),
                    start_id=kp_counter + 1,
                    content=chunk,
                )

            messages = [
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": user_prompt},
            ]

            response = await self._call_llm(messages)
            chunk_kps = self._parse_response(response, kp_counter)
            all_kps.extend(chunk_kps)
            kp_counter = len(all_kps)

        logger.info("Phase 1: extracted %d knowledge points total", len(all_kps))
        return ExtractionResult(title=title, knowledge_points=all_kps)

    def _parse_response(self, response: str, offset: int) -> list[KnowledgePoint]:
        """解析 LLM 返回的 JSON，重新编号"""
        # 提取 JSON 块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个响应
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Phase 1: failed to parse LLM response as JSON, attempting recovery")
            # 尝试修复常见的 JSON 问题
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                logger.error("Phase 1: JSON recovery failed, returning empty list")
                return []

        raw_kps = data.get("knowledge_points", [])
        result: list[KnowledgePoint] = []

        for idx, kp_data in enumerate(raw_kps):
            kp_id = f"KP-{offset + idx + 1:03d}"
            result.append(KnowledgePoint(
                id=kp_id,
                type=kp_data.get("type", "concept"),
                statement=kp_data.get("statement", ""),
                source_section=kp_data.get("source_section", ""),
                source_text=kp_data.get("source_text", ""),
                keywords=kp_data.get("keywords", []),
            ))

        return result
