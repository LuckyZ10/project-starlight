"""Tests for starlight.factory module"""
import json
import pytest
from unittest.mock import AsyncMock

from starlight.factory.extractor import KnowledgeExtractor, KnowledgePoint, ExtractionResult
from starlight.factory.builder import NodeBuilder, NodeSpec, BuildResult
from starlight.factory.auditor import CoverageAuditor, CoverageReport
from starlight.factory.validator import CrossValidator, ValidationResult
from starlight.factory.pipeline import CartridgeFactory


# ── Fixtures ──────────────────────────────────────────────────

def make_fake_llm(responses: list[str]):
    """创建一个返回预设响应的假 LLM"""
    call_count = 0

    async def fake_llm(messages):
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    return fake_llm


def make_fake_llm_no_second_pass(responses: list[str]):
    """创建假 LLM，禁用二次查漏（减少需要的 mock 数量）"""
    call_count = 0

    async def fake_llm(messages):
        nonlocal call_count
        idx = min(call_count, len(responses) - 1)
        call_count += 1
        return responses[idx]

    return fake_llm


EXTRACTION_RESPONSE = """```json
{
  "title": "测试课程",
  "total_kps": 6,
  "knowledge_points": [
    {"id": "KP-001", "type": "concept", "statement": "变量的定义", "source_section": "1.1", "source_text": "变量是存储数据的容器", "keywords": ["变量", "赋值"], "importance": "core"},
    {"id": "KP-002", "type": "concept", "statement": "赋值运算符", "source_section": "1.1", "source_text": "= 是赋值不是等于", "keywords": ["赋值", "运算符"], "importance": "core"},
    {"id": "KP-003", "type": "fact", "statement": "Python 动态类型", "source_section": "1.2", "source_text": "Python不需要声明类型", "keywords": ["类型", "动态"], "importance": "important"},
    {"id": "KP-004", "type": "concept", "statement": "整数类型", "source_section": "1.2", "source_text": "整数是 int 类型", "keywords": ["int", "整数"], "importance": "important"},
    {"id": "KP-005", "type": "concept", "statement": "字符串类型", "source_section": "1.2", "source_text": "字符串是 str 类型", "keywords": ["str", "字符串"], "importance": "important"},
    {"id": "KP-006", "type": "procedure", "statement": "类型转换", "source_section": "1.3", "source_text": "用 int() 做类型转换", "keywords": ["类型转换", "int"], "importance": "important"}
  ]
}
```"""

MISS_RESPONSE = """```json
{
  "missed_count": 0,
  "missed_points": []
}
```"""

BUILD_RESPONSE = """```json
{
  "nodes": [
    {
      "id": "N01",
      "title": "变量与赋值",
      "kp_ids": ["KP-001", "KP-002"],
      "prerequisites": [],
      "difficulty": 1,
      "pass_criteria": "能解释变量的概念并写出赋值语句",
      "summary": "变量基础概念"
    },
    {
      "id": "N02",
      "title": "数据类型",
      "kp_ids": ["KP-003", "KP-004", "KP-005"],
      "prerequisites": ["N01"],
      "difficulty": 1,
      "pass_criteria": "能区分 int/str/float 并正确使用",
      "summary": "基本数据类型"
    },
    {
      "id": "N03",
      "title": "类型转换",
      "kp_ids": ["KP-006"],
      "prerequisites": ["N02"],
      "difficulty": 2,
      "pass_criteria": "能用 int() str() float() 进行类型转换",
      "summary": "类型转换操作"
    }
  ],
  "dag": {
    "entry": "N01",
    "edges": {"N01": ["N02"], "N02": ["N03"], "N03": []}
  }
}
```"""

NODE_CONTENT_RESPONSE_N01 = """# 变量与赋值

## 核心概念
变量是存储数据的容器。

```python
name = "Alice"
age = 25
```

## 赋值的本质
`=` 是赋值运算符，不是数学中的等于。"""

NODE_CONTENT_RESPONSE_N02 = """# 数据类型

## 核心概念
Python 是动态类型语言，不需要声明类型。

## 常见类型
- int: 整数
- str: 字符串
- float: 浮点数"""

NODE_CONTENT_RESPONSE_N03 = """# 类型转换

## 核心概念
使用 int() str() float() 进行类型转换。

```python
x = int("42")
```"""

AUDIT_RESPONSE = """```json
{
  "coverage_report": {
    "total": 6,
    "full": 6,
    "partial": 0,
    "missing": 0,
    "distorted": 0,
    "coverage_percent": 100.0
  },
  "details": [
    {"kp_id": "KP-001", "status": "FULL", "mapped_node": "N01", "evidence": "变量是存储数据的容器", "issue": ""},
    {"kp_id": "KP-002", "status": "FULL", "mapped_node": "N01", "evidence": "= 是赋值运算符", "issue": ""},
    {"kp_id": "KP-003", "status": "FULL", "mapped_node": "N02", "evidence": "动态类型", "issue": ""},
    {"kp_id": "KP-004", "status": "FULL", "mapped_node": "N02", "evidence": "int 整数", "issue": ""},
    {"kp_id": "KP-005", "status": "FULL", "mapped_node": "N02", "evidence": "str 字符串", "issue": ""},
    {"kp_id": "KP-006", "status": "FULL", "mapped_node": "N03", "evidence": "int() 类型转换", "issue": ""}
  ]
}
```"""

VALIDATE_RESPONSE = """```json
{
  "issues": [
    {
      "severity": "suggestion",
      "category": "assessment",
      "location": "N01",
      "description": "通过标准可以更具体",
      "suggestion": "添加'能写出至少2种赋值语句'"
    }
  ],
  "summary": "整体良好，仅有一个建议级别问题"
}
```"""


# ── Tests ─────────────────────────────────────────────────────

class TestKnowledgeExtractor:
    @pytest.mark.asyncio
    async def test_extract_single_chunk(self):
        fake_llm = make_fake_llm([EXTRACTION_RESPONSE, MISS_RESPONSE])
        extractor = KnowledgeExtractor(fake_llm, enable_second_pass=True)

        result = await extractor.extract("测试课程", "一些测试内容")

        assert isinstance(result, ExtractionResult)
        assert result.total == 6
        assert result.knowledge_points[0].id.startswith("KP-")
        assert result.knowledge_points[0].type == "concept"
        assert result.knowledge_points[0].importance == "core"

    @pytest.mark.asyncio
    async def test_extract_preserves_types(self):
        fake_llm = make_fake_llm([EXTRACTION_RESPONSE, MISS_RESPONSE])
        extractor = KnowledgeExtractor(fake_llm)

        result = await extractor.extract("测试", "内容")

        types = {kp.type for kp in result.knowledge_points}
        assert "concept" in types
        assert "fact" in types
        assert "procedure" in types

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """测试重复知识点去重"""
        dedup_response = """```json
        {
          "title": "测试",
          "total_kps": 3,
          "knowledge_points": [
            {"id": "KP-001", "type": "concept", "statement": "变量是存储数据的容器", "source_section": "1.1", "source_text": "内容", "keywords": ["变量"], "importance": "core"},
            {"id": "KP-002", "type": "concept", "statement": "变量是存储数据的容器", "source_section": "1.1", "source_text": "内容", "keywords": ["变量"], "importance": "core"},
            {"id": "KP-003", "type": "fact", "statement": "Python 是解释型语言", "source_section": "1.2", "source_text": "内容", "keywords": ["python"], "importance": "important"}
          ]
        }
        ```"""
        fake_llm = make_fake_llm([dedup_response, MISS_RESPONSE])
        extractor = KnowledgeExtractor(fake_llm)

        result = await extractor.extract("测试", "内容")

        assert result.total == 2  # KP-001 和 KP-002 是重复的

    @pytest.mark.asyncio
    async def test_second_pass_finds_missed(self):
        """测试二次查漏能发现遗漏的知识点"""
        miss_found_response = """```json
        {
          "missed_count": 1,
          "missed_points": [
            {"id": "KP-MISS-001", "type": "fact", "statement": "Python 3 默认编码是 UTF-8", "source_section": "1.4", "source_text": "默认编码是 UTF-8", "keywords": ["编码", "UTF-8"], "importance": "detail", "why_missed": "在段落末尾"}
          ]
        }
        ```"""
        fake_llm = make_fake_llm([EXTRACTION_RESPONSE, miss_found_response])
        extractor = KnowledgeExtractor(fake_llm, enable_second_pass=True)

        result = await extractor.extract("测试", "内容")

        assert result.total == 7  # 原始 6 + 补漏 1


class TestNodeBuilder:
    @pytest.mark.asyncio
    async def test_build_creates_nodes(self):
        fake_llm = make_fake_llm([
            BUILD_RESPONSE,
            NODE_CONTENT_RESPONSE_N01,
            NODE_CONTENT_RESPONSE_N02,
            NODE_CONTENT_RESPONSE_N03,
        ])
        builder = NodeBuilder(fake_llm)

        extraction = ExtractionResult(
            title="测试",
            knowledge_points=[
                KnowledgePoint("KP-001", "concept", "变量的定义", "1.1", "变量是容器", ["变量"], "core"),
                KnowledgePoint("KP-002", "concept", "赋值", "1.1", "=是赋值", ["赋值"], "core"),
                KnowledgePoint("KP-003", "fact", "动态类型", "1.2", "不用声明类型", ["类型"], "important"),
                KnowledgePoint("KP-004", "concept", "整数", "1.2", "整数是int", ["int"], "important"),
                KnowledgePoint("KP-005", "concept", "字符串", "1.2", "字符串是str", ["str"], "important"),
                KnowledgePoint("KP-006", "procedure", "类型转换", "1.3", "用int()", ["转换"], "important"),
            ],
        )

        result = await builder.build(extraction)

        assert isinstance(result, BuildResult)
        assert len(result.nodes) == 3
        assert result.dag_entry == "N01"
        assert "N02" in result.dag_edges["N01"]
        # 节点内容已生成
        assert all(n.content for n in result.nodes)

    @pytest.mark.asyncio
    async def test_manifest_generation(self):
        fake_llm = make_fake_llm([
            BUILD_RESPONSE,
            NODE_CONTENT_RESPONSE_N01,
            NODE_CONTENT_RESPONSE_N02,
            NODE_CONTENT_RESPONSE_N03,
        ])
        builder = NodeBuilder(fake_llm)

        extraction = ExtractionResult(
            title="测试",
            knowledge_points=[
                KnowledgePoint("KP-001", "concept", "变量", "1.1", "内容", [], "core"),
            ],
        )
        result = await builder.build(extraction)
        manifest = result.to_manifest("test-course", "测试课程")

        assert manifest["id"] == "test-course"
        assert manifest["title"] == "测试课程"
        assert "nodes" in manifest
        assert "dag" in manifest


class TestCoverageAuditor:
    @pytest.mark.asyncio
    async def test_audit_full_coverage(self):
        fake_llm = make_fake_llm([AUDIT_RESPONSE])
        auditor = CoverageAuditor(fake_llm)

        extraction = ExtractionResult(
            title="测试",
            knowledge_points=[
                KnowledgePoint(f"KP-{i:03d}", "concept", f"知识点{i}", "1.1", "内容", [], "important")
                for i in range(1, 7)
            ],
        )
        build = BuildResult(
            nodes=[
                NodeSpec("N01", "测试", ["KP-001", "KP-002"], [], 1, "标准", "摘要", "内容"),
                NodeSpec("N02", "测试2", ["KP-003", "KP-004", "KP-005"], ["N01"], 1, "标准", "摘要", "内容"),
                NodeSpec("N03", "测试3", ["KP-006"], ["N02"], 2, "标准", "摘要", "内容"),
            ],
            dag_entry="N01",
            dag_edges={"N01": ["N02"], "N02": ["N03"], "N03": []},
        )

        report = await auditor.audit(extraction, build)

        assert isinstance(report, CoverageReport)
        assert report.coverage_percent == 100.0
        assert report.is_passing is True

    @pytest.mark.asyncio
    async def test_audit_identifies_gaps(self):
        gap_response = """```json
{
  "coverage_report": {"total": 3, "full": 2, "partial": 0, "missing": 1, "distorted": 0, "coverage_percent": 66.7},
  "details": [
    {"kp_id": "KP-001", "status": "FULL", "mapped_node": "N01", "evidence": "找到", "issue": ""},
    {"kp_id": "KP-002", "status": "FULL", "mapped_node": "N01", "evidence": "找到", "issue": ""},
    {"kp_id": "KP-003", "status": "MISSING", "mapped_node": "", "evidence": "", "issue": "未在教学内容中出现"}
  ]
}
```"""
        fake_llm = make_fake_llm([gap_response])
        auditor = CoverageAuditor(fake_llm)

        extraction = ExtractionResult(
            title="测试",
            knowledge_points=[
                KnowledgePoint("KP-001", "concept", "A", "1", "a", [], "important"),
                KnowledgePoint("KP-002", "concept", "B", "1", "b", [], "important"),
                KnowledgePoint("KP-003", "concept", "C", "1", "c", [], "important"),
            ],
        )
        build = BuildResult(
            nodes=[NodeSpec("N01", "测试", ["KP-001", "KP-002"], [], 1, "标准", "摘要", "内容")],
            dag_entry="N01",
            dag_edges={"N01": []},
        )

        report = await auditor.audit(extraction, build)

        assert report.coverage_percent == 66.7
        assert report.is_passing is False
        assert "KP-003" in report.gap_kp_ids


class TestCrossValidator:
    @pytest.mark.asyncio
    async def test_validate_returns_issues(self):
        fake_llm = make_fake_llm([VALIDATE_RESPONSE] * 4)
        validator = CrossValidator(fake_llm)

        extraction = ExtractionResult(
            title="测试",
            knowledge_points=[KnowledgePoint("KP-001", "concept", "变量", "1", "内容", ["变量"], "core")],
        )
        build = BuildResult(
            nodes=[NodeSpec("N01", "变量", ["KP-001"], [], 1, "能解释变量", "摘要", "内容" * 10)],
            dag_entry="N01",
            dag_edges={"N01": []},
        )

        result = await validator.validate("测试课程", extraction, build)

        assert isinstance(result, ValidationResult)
        assert result.critical_count == 0
        assert len(result.issues) >= 1
        assert result.is_passing is True


class TestCartridgeFactoryIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        """端到端测试：原始文本 → .star 卡带"""
        responses = [
            EXTRACTION_RESPONSE,               # Phase 1 round 1
            MISS_RESPONSE,                     # Phase 1 round 2 (查漏)
            BUILD_RESPONSE,                    # Phase 2: 分组
            NODE_CONTENT_RESPONSE_N01,          # Phase 2.5: N01 内容
            NODE_CONTENT_RESPONSE_N02,          # Phase 2.5: N02 内容
            NODE_CONTENT_RESPONSE_N03,          # Phase 2.5: N03 内容
            AUDIT_RESPONSE,                     # Phase 3
            VALIDATE_RESPONSE,                  # Phase 4 × 4
            VALIDATE_RESPONSE,
            VALIDATE_RESPONSE,
            VALIDATE_RESPONSE,
        ]
        fake_llm = make_fake_llm(responses)
        factory = CartridgeFactory(fake_llm)

        output = await factory.manufacture(
            title="测试课程",
            content="# 测试\n\n变量是存储数据的容器。",
            cartridge_id="test-course",
            output_dir=str(tmp_path),
        )

        assert output.total_kps == 6
        assert output.total_nodes == 3
        assert output.coverage == 100.0
        assert output.validation.is_passing is True

        # 检查文件是否写入
        import os
        assert os.path.isdir(output.cartridge_dir)
        assert os.path.isfile(output.manifest_path)

        # 验证 manifest 内容
        with open(output.manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["id"] == "test-course"
        assert len(manifest["nodes"]) == 3

        # 验证节点文件存在
        for node_entry in manifest["nodes"]:
            node_file = os.path.join(output.cartridge_dir, node_entry["file"])
            assert os.path.isfile(node_file), f"Missing node file: {node_file}"

    @pytest.mark.asyncio
    async def test_summary_output(self, tmp_path):
        responses = [
            EXTRACTION_RESPONSE,
            MISS_RESPONSE,
            BUILD_RESPONSE,
            NODE_CONTENT_RESPONSE_N01,
            NODE_CONTENT_RESPONSE_N02,
            NODE_CONTENT_RESPONSE_N03,
            AUDIT_RESPONSE,
            VALIDATE_RESPONSE, VALIDATE_RESPONSE, VALIDATE_RESPONSE, VALIDATE_RESPONSE,
        ]
        fake_llm = make_fake_llm(responses)
        factory = CartridgeFactory(fake_llm)

        output = await factory.manufacture(
            title="测试",
            content="内容",
            cartridge_id="test",
            output_dir=str(tmp_path),
        )

        summary = output.summary()
        assert "test" in summary
        assert "100.0%" in summary

    @pytest.mark.asyncio
    async def test_pipeline_without_second_pass(self, tmp_path):
        """测试禁用二次查漏的流程"""
        responses = [
            EXTRACTION_RESPONSE,               # Phase 1 round 1 only
            BUILD_RESPONSE,                    # Phase 2
            NODE_CONTENT_RESPONSE_N01,
            NODE_CONTENT_RESPONSE_N02,
            NODE_CONTENT_RESPONSE_N03,
            AUDIT_RESPONSE,                     # Phase 3
            VALIDATE_RESPONSE,                  # Phase 4 × 4
            VALIDATE_RESPONSE,
            VALIDATE_RESPONSE,
            VALIDATE_RESPONSE,
        ]
        fake_llm = make_fake_llm(responses)
        factory = CartridgeFactory(fake_llm)
        factory.extractor.enable_second_pass = False  # 禁用二次查漏

        output = await factory.manufacture(
            title="测试",
            content="内容",
            cartridge_id="test-nosp",
            output_dir=str(tmp_path),
        )

        assert output.total_kps == 6
        assert output.coverage == 100.0
