"""End-to-end integration tests for the Starlight learning flow."""
import pytest
from unittest.mock import AsyncMock

from starlight.core.cartridge import CartridgeLoader
from starlight.core.assessor import Assessor, AssessmentResult
from starlight.core.harness import LearningHarness
from starlight.core.contributor import TributeEngine
from starlight.main import MockProgressManager


@pytest.fixture
def full_harness():
    """Create a harness with real cartridge loader and mock LLM."""
    loader = CartridgeLoader("./cartridges")
    assessor = Assessor(llm_model="test", llm_api_key="test")
    # Mock the LLM call to avoid real API calls
    assessor._call_llm = AsyncMock()
    progress_mgr = MockProgressManager()
    tribute = TributeEngine()
    return LearningHarness(loader, assessor, progress_mgr, tribute)


@pytest.mark.asyncio
async def test_full_learning_flow(full_harness):
    """Simulate: /browse → /start → answer → PASS → progress"""
    # 1. Browse
    result = await full_harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text
    assert result.state == "idle"

    # 2. Start
    result = await full_harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    assert result.state == "learning"
    assert "Python" in result.text or "变量" in result.text

    # 3. Answer (mock LLM returns PASS)
    full_harness.assessor._call_llm.return_value = "非常好，你理解了变量赋值！[PASS]"
    result = await full_harness.process(user_id=1, message="变量是存数据的", cartridge_id="python-basics")
    assert result.verdict == "PASS"

    # 4. Check progress
    result = await full_harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert result.state == "in_progress"


@pytest.mark.asyncio
async def test_browse_lists_all_cartridges(full_harness):
    result = await full_harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text
    assert result.state == "idle"


@pytest.mark.asyncio
async def test_help_shows_commands(full_harness):
    result = await full_harness.process(user_id=1, message="/help")
    assert "/browse" in result.text
    assert "/start" in result.text
    assert "/progress" in result.text


@pytest.mark.asyncio
async def test_start_nonexistent_cartridge():
    loader = CartridgeLoader("./cartridges")
    assessor = AsyncMock()
    progress = MockProgressManager()
    tribute = TributeEngine()
    harness = LearningHarness(loader, assessor, progress, tribute)

    with pytest.raises(FileNotFoundError):
        await harness.process(user_id=1, message="/start", cartridge_id="nonexistent")
