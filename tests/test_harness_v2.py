# tests/test_harness_v2.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from starlight.core.harness_v2 import LearningHarnessV2
from starlight.core.assessor_v2 import AssessorV2
from starlight.core.strategies import SocraticStrategy
from starlight.core.contributor import TributeEngine
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile
from starlight.main import MockProgressManager


@pytest.fixture
def mock_node_n01():
    return {
        "id": "N01", "title": "变量",
        "file": "nodes/N01.md", "prerequisites": [],
        "difficulty": 1, "pass_criteria": "能写赋值语句",
    }


@pytest.fixture
def mock_node_n02():
    return {
        "id": "N02", "title": "类型",
        "file": "nodes/N02.md", "prerequisites": ["N01"],
        "difficulty": 1, "pass_criteria": "能区分类型",
    }


@pytest.fixture
def harness(mock_node_n01, mock_node_n02):
    loader = MagicMock()
    loader.list_cartridges.return_value = ["python-basics"]
    loader.load.return_value = {
        "id": "python-basics",
        "title": "Python",
        "nodes": [mock_node_n01, mock_node_n02],
        "dag": {
            "entry": "N01",
            "edges": {"N01": ["N02"], "N02": []},
        },
    }
    loader.get_entry_node.return_value = mock_node_n01
    loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    loader.get_next_nodes.return_value = [mock_node_n02]
    loader.get_node_by_id.return_value = mock_node_n01

    assessor = AssessorV2(
        llm_model="test", llm_api_key="test",
        strategy=SocraticStrategy()
    )
    assessor._call_llm = AsyncMock()

    progress = MockProgressManager()
    tribute = TributeEngine()

    return LearningHarnessV2(
        loader, assessor, progress, tribute,
        strategy_name="socratic"
    )


@pytest.mark.asyncio
async def test_start_creates_session(harness):
    harness.assessor._call_llm.return_value = "来考考你：什么是变量？"
    result = await harness.process(
        user_id=1, message="/start", cartridge_id="python-basics"
    )
    assert result.state == "learning"
    session = harness.get_session(1, "python-basics")
    assert session is not None
    assert session.current_node == "N01"


@pytest.mark.asyncio
async def test_full_flow(harness, mock_node_n01):
    # Start
    harness.assessor._call_llm.return_value = "来考考你：什么是变量？"
    await harness.process(
        user_id=1, message="/start", cartridge_id="python-basics"
    )

    # Answer — LLM returns PASS
    harness.assessor._call_llm.return_value = "非常好！[PASS]"
    harness.cartridges.get_node_by_id.return_value = mock_node_n01
    result = await harness.process(
        user_id=1, message="变量就是存数据的盒子",
        cartridge_id="python-basics"
    )
    assert result.verdict == "PASS"

    # Check learner profile updated
    learner = harness.get_learner(1)
    assert learner.total_xp > 0
    assert learner.nodes_completed == 1


@pytest.mark.asyncio
async def test_continue_flow(harness, mock_node_n01):
    harness.assessor._call_llm.return_value = "来考考你"
    await harness.process(
        user_id=1, message="/start", cartridge_id="python-basics"
    )

    harness.assessor._call_llm.return_value = "你能更具体地说明吗？"
    harness.cartridges.get_node_by_id.return_value = mock_node_n01
    result = await harness.process(
        user_id=1, message="存东西的", cartridge_id="python-basics"
    )
    assert result.verdict == "CONTINUE"

    # Session has conversation history
    session = harness.get_session(1, "python-basics")
    assert len(session.conversation) >= 3


@pytest.mark.asyncio
async def test_fail_flow(harness, mock_node_n01):
    harness.assessor._call_llm.return_value = "来考考你"
    await harness.process(
        user_id=1, message="/start", cartridge_id="python-basics"
    )

    harness.assessor._call_llm.return_value = (
        "[FAIL] 还不够。建议：再想想变量的本质。"
    )
    harness.cartridges.get_node_by_id.return_value = mock_node_n01
    result = await harness.process(
        user_id=1, message="不知道", cartridge_id="python-basics"
    )
    assert result.verdict == "FAIL"
    assert "提示" in result.text


@pytest.mark.asyncio
async def test_stats(harness):
    result = await harness.process(user_id=1, message="/stats")
    assert "XP" in result.text
    assert "知识水平" in result.text


@pytest.mark.asyncio
async def test_help(harness):
    result = await harness.process(user_id=1, message="/help")
    assert "V2" in result.text
    assert "/browse" in result.text


@pytest.mark.asyncio
async def test_browse(harness):
    result = await harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text


@pytest.mark.asyncio
async def test_review_no_cards(harness):
    result = await harness.process(user_id=1, message="/review")
    assert "暂无" in result.text


@pytest.mark.asyncio
async def test_start_without_cartridge_id(harness):
    result = await harness.process(user_id=1, message="/start")
    assert "卡带ID" in result.text


@pytest.mark.asyncio
async def test_message_without_session(harness):
    result = await harness.process(
        user_id=1, message="hello", cartridge_id="python-basics"
    )
    assert result.state == "idle"
    assert "请先" in result.text


@pytest.mark.asyncio
async def test_message_without_cartridge(harness):
    result = await harness.process(user_id=1, message="hello")
    assert result.state == "idle"


@pytest.mark.asyncio
async def test_learner_profile_persistence(harness, mock_node_n01):
    """Learner profile persists across interactions"""
    harness.assessor._call_llm.return_value = "来考考你"
    await harness.process(
        user_id=1, message="/start", cartridge_id="python-basics"
    )

    harness.assessor._call_llm.return_value = "很好！[PASS]"
    harness.cartridges.get_node_by_id.return_value = mock_node_n01
    await harness.process(
        user_id=1, message="answer", cartridge_id="python-basics"
    )

    learner = harness.get_learner(1)
    assert learner.nodes_completed == 1
    assert len(learner.error_patterns) == 0
