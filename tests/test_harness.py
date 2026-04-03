import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.harness import LearningHarness
from starlight.core.assessor import AssessmentResult


@pytest.fixture
def mock_deps():
    cartridge_loader = MagicMock()
    cartridge_loader.load.return_value = {
        "id": "python-basics",
        "title": "Python",
        "nodes": [
            {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"},
            {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
        ],
        "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": []}},
    }
    cartridge_loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    cartridge_loader.get_entry_node.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    cartridge_loader.get_next_nodes.return_value = [{"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"}]
    cartridge_loader.get_node_by_id.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}

    assessor = AsyncMock()
    progress_mgr = AsyncMock()
    tribute_engine = MagicMock()

    return cartridge_loader, assessor, progress_mgr, tribute_engine


@pytest.mark.asyncio
async def test_new_user_start(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    assert result.state == "learning"
    assert "变量" in result.text


@pytest.mark.asyncio
async def test_assessment_pass(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(current_node="N01", status="in_progress", cartridge_id="python-basics")
    assessor.assess.return_value = AssessmentResult(verdict="PASS", feedback="很好！", score=85)

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="变量就是存数据的盒子", cartridge_id="python-basics")
    assert result.verdict == "PASS"
    assert result.next_node == "N02"


@pytest.mark.asyncio
async def test_assessment_fail(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(current_node="N01", status="in_progress", cartridge_id="python-basics")
    assessor.assess.return_value = AssessmentResult(verdict="FAIL", feedback="还不够", score=0, hint="想想语法")

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="不知道", cartridge_id="python-basics")
    assert result.verdict == "FAIL"
    assert result.state == "learning"


@pytest.mark.asyncio
async def test_assessment_continue(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(current_node="N01", status="in_progress", cartridge_id="python-basics")
    assessor.assess.return_value = AssessmentResult(verdict="CONTINUE", feedback="再具体说说", score=0)

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="变量就是盒子", cartridge_id="python-basics")
    assert result.verdict == "CONTINUE"
    assert result.state == "learning"


@pytest.mark.asyncio
async def test_complete_cartridge(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(current_node="N03", status="in_progress", cartridge_id="python-basics")
    assessor.assess.return_value = AssessmentResult(verdict="PASS", feedback="完美！", score=95)
    loader.get_next_nodes.return_value = []
    tribute.build_completion_tribute.return_value = "恭喜通关"

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="最后一个回答", cartridge_id="python-basics")
    assert result.state == "completed"


@pytest.mark.asyncio
async def test_already_completed(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(status="completed", cartridge_id="python-basics")

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/study", cartridge_id="python-basics")
    assert result.state == "completed"
    assert "通关" in result.text


@pytest.mark.asyncio
async def test_no_progress_no_start(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="变量", cartridge_id="python-basics")
    assert result.state == "idle"
    assert "/start" in result.text
