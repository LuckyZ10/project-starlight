# starlight/factory/extractor.py
"""Phase 1: 知识点原子提取 — 从原始 MD 提取不可再分的知识点

包含两轮提取：
  第一轮：逐块提取所有知识点
  第二轮：对照原文逐块查漏补缺
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from starlight.factory.prompts import (
    EXTRACT_SYSTEM, EXTRACT_USER, EXTRACT_CHUNK_USER,
    EXTRACT_MISS_SYSTEM, EXTRACT_MISS_USER,
)

logger = logging.getLogger(__name__)


@dataclass
class KnowledgePoint:
    id: str                    # KP-001
    type: str                  # fact|concept|formula|procedure|example|engineering|comparison|structure
    statement: str             # 完整描述
    source_section: str        # 原文章节位置
    source_text: str           # 原文片段
    keywords: list[str] = field(default_factory=list)
    importance: str = "important"  # core|important|detail


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
                    "importance": kp.importance,
                }
                for kp in self.knowledge_points
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def deduplicate(self) -> None:
        """去除重复的知识点（基于 statement 相似度）"""
        seen_statements: dict[str, str] = {}  # normalized -> id
        unique: list[KnowledgePoint] = []

        for kp in self.knowledge_points:
            # 归一化：去空格、转小写、取前 80 字符
            normalized = re.sub(r'\s+', '', kp.statement.lower())[:80]
            if normalized in seen_statements:
                logger.debug("Dedup: merging %s into %s", kp.id, seen_statements[normalized])
                continue
            seen_statements[normalized] = kp.id
            unique.append(kp)

        removed = len(self.knowledge_points) - len(unique)
        if removed > 0:
            logger.info("Deduplication: removed %d duplicate KPs", removed)
        self.knowledge_points = unique

        # 重新编号
        for i, kp in enumerate(self.knowledge_points):
            kp.id = f"KP-{i + 1:03d}"


class KnowledgeExtractor:
    """Phase 1: 从原始文档中提取知识点原子（两轮提取 + 去重）"""

    def __init__(self, llm_call_fn, chunk_max_chars: int = 12000,
                 enable_second_pass: bool = True):
        """
        Args:
            llm_call_fn: async callable(messages) -> str
            chunk_max_chars: 每个分块的最大字符数
            enable_second_pass: 是否启用二次查漏（默认开启）
        """
        self._call_llm = llm_call_fn
        self.chunk_max_chars = chunk_max_chars
        self.enable_second_pass = enable_second_pass

    def _chunk_text(self, text: str) -> list[str]:
        """按章节分块，尽量在标题处切割"""
        # 按二级/三级标题切割
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

        # 如果只有一个超大块，按段落切
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
        """从文档中提取所有知识点原子（两轮 + 去重）"""
        chunks = self._chunk_text(content)
        logger.info("Phase 1: splitting into %d chunks (total %d chars)", len(chunks), len(content))

        # ============================================================
        # 第一轮：逐块提取
        # ============================================================
        all_kps: list[KnowledgePoint] = []
        kp_counter = 0

        for i, chunk in enumerate(chunks):
            logger.info("Phase 1 round 1: extracting chunk %d/%d", i + 1, len(chunks))

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

        logger.info("Phase 1 round 1: extracted %d knowledge points", len(all_kps))

        # ============================================================
        # 第二轮：查漏补缺
        # ============================================================
        if self.enable_second_pass:
            all_kps = await self._second_pass(title, content, chunks, all_kps)

        # ============================================================
        # 去重 + 重编号
        # ============================================================
        result = ExtractionResult(title=title, knowledge_points=all_kps)
        result.deduplicate()

        logger.info("Phase 1 complete: %d unique knowledge points after dedup", result.total)
        return result

    async def _second_pass(self, title: str, content: str,
                           chunks: list[str], existing_kps: list[KnowledgePoint]) -> list[KnowledgePoint]:
        """第二轮提取：逐块查漏补缺"""
        logger.info("Phase 1 round 2: checking for missed knowledge points...")

        missed_total = 0

        for i, chunk in enumerate(chunks):
            # 构建已提取知识点摘要（与当前块相关的）
            existing_summary = self._summarize_existing_kps(chunk, existing_kps)

            user_prompt = EXTRACT_MISS_USER.format(
                content=chunk,
                existing_count=len(existing_kps),
                existing_kps=existing_summary,
            )

            messages = [
                {"role": "system", "content": EXTRACT_MISS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ]

            response = await self._call_llm(messages)
            missed_kps = self._parse_miss_response(response)
            missed_total += len(missed_kps)
            existing_kps.extend(missed_kps)

            logger.info("  chunk %d/%d: found %d missed points", i + 1, len(chunks), len(missed_kps))

        logger.info("Phase 1 round 2: found %d additional knowledge points", missed_total)
        return existing_kps

    def _summarize_existing_kps(self, chunk: str, kps: list[KnowledgePoint]) -> str:
        """构建与当前块相关的已提取知识点摘要"""
        # 提取当前块的关键词
        chunk_words = set(re.findall(r'[\w\u4e00-\u9fff]{2,}', chunk.lower()))

        relevant = []
        for kp in kps:
            # 检查关键词重叠
            kp_words = set(w.lower() for w in kp.keywords)
            overlap = kp_words & chunk_words
            if overlap or kp.source_text[:50] in chunk:
                relevant.append(f"- [{kp.type}] {kp.statement}")

        if not relevant:
            # 没有直接相关的，列出所有（摘要）
            return "\n".join(f"- [{kp.type}] {kp.statement}" for kp in kps[:50])

        return "\n".join(relevant[:50])

    def _parse_response(self, response: str, offset: int) -> list[KnowledgePoint]:
        """解析第一轮提取的 LLM 返回"""
        json_str = self._extract_json(response)
        if not json_str:
            return []

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            json_str = self._repair_json(json_str)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                logger.error("Phase 1: JSON parse failed after repair")
                return []

        # 容错：LLM 可能返回 list 或 dict
        if isinstance(data, list):
            raw_kps = data
        elif isinstance(data, dict):
            raw_kps = data.get("knowledge_points", [])
        else:
            raw_kps = []
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
                importance=kp_data.get("importance", "important"),
            ))

        return result

    def _parse_miss_response(self, response: str) -> list[KnowledgePoint]:
        """解析第二轮查漏的 LLM 返回"""
        json_str = self._extract_json(response)
        if not json_str:
            return []

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return []

        missed = data.get("missed_points", [])
        result: list[KnowledgePoint] = []

        for idx, kp_data in enumerate(missed):
            # 用 MISS 前缀标记第二轮补充的知识点
            kp_id = f"KP-MISS-{idx + 1:03d}"
            result.append(KnowledgePoint(
                id=kp_id,
                type=kp_data.get("type", "concept"),
                statement=kp_data.get("statement", ""),
                source_section=kp_data.get("source_section", ""),
                source_text=kp_data.get("source_text", ""),
                keywords=kp_data.get("keywords", []),
                importance=kp_data.get("importance", "important"),
            ))

        return result

    @staticmethod
    def _extract_json(response: str) -> str | None:
        """从 LLM 响应中提取 JSON 块"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json_match.group(1)
        # 尝试直接当作 JSON
        if response.strip().startswith("{") or response.strip().startswith("["):
            return response.strip()
        return None

    @staticmethod
    def _repair_json(json_str: str) -> str:
        """尝试修复常见的 JSON 格式问题"""
        # 去除尾部逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        # 修复未转义的换行符
        json_str = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', '\\n', json_str)
        return json_str
