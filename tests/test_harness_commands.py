import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.harness import LearningHarness


@pytest.fixture
def mock_deps():
    loader = MagicMock()
    loader.list_cartridges.return_value = ["python-basics", "git-essentials"]
    loader.load.return_value = {
        "id": "python-basics",
        "title": "Python 基础",
        "nodes": [
            {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"},
            {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
        ],
        "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": []}},
    }
    loader.get_entry_node.return_value = {
        "id": "N01", "title": "变量", "file": "nodes/N01.md",
        "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句",
    }
    loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    loader.get_next_nodes.return_value = [
        {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
    ]
    loader.get_node_by_id.return_value = {
        "id": "N01", "title": "变量", "file": "nodes/N01.md",
        "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句",
    }

    assessor = AsyncMock()
    progress = AsyncMock()
    tribute = MagicMock()
    return loader, assessor, progress, tribute


@pytest.mark.asyncio
async def test_browse_cartridges(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text
    assert "git-essentials" in result.text
    assert result.state == "idle"


@pytest.mark.asyncio
async def test_progress_command(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(
        current_node="N02",
        status="in_progress",
        cartridge_id="python-basics",
    )
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert "N02" in result.text or "进度" in result.text


@pytest.mark.asyncio
async def test_progress_no_progress(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert "尚未开始" in result.text or "没有" in result.text or "还没" in result.text or result.state == "idle"


@pytest.mark.asyncio
async def test_help_command(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/help")
    assert "/start" in result.text
    assert "/browse" in result.text
    assert "/progress" in result.text


@pytest.mark.asyncio
async def test_review_command_no_cartridge(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/review")
    assert "请先选择一个卡带" in result.text or "卡带" in result.text


@pytest.mark.asyncio
async def test_review_command_no_progress(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/review", cartridge_id="python-basics")
    assert "还没" in result.text or "尚未" in result.text or "/start" in result.text
