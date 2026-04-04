import pytest
from starlight.core.strategies import (
    SocraticStrategy, FeynmanStrategy, ScaffoldStrategy,
    AdaptiveStrategy, get_strategy
)
from starlight.core.learner import LearnerProfile, ZPDZone
from starlight.core.session import Session


@pytest.fixture
def novice():
    return LearnerProfile(user_id=1, knowledge_level=0.1, confidence=0.2)


@pytest.fixture
def expert():
    return LearnerProfile(user_id=2, knowledge_level=0.8, confidence=0.9, bloom_level=4)


@pytest.fixture
def session():
    return Session(user_id=1, cartridge_id="py", current_node="N01")


@pytest.mark.asyncio
async def test_socratic_builds_prompt(novice, session):
    s = SocraticStrategy()
    prompt = await s.build_system_prompt("变量是存数据的", "能写赋值语句", novice, session)
    assert "苏格拉底" in prompt
    assert "变量是存数据的" in prompt


@pytest.mark.asyncio
async def test_socratic_pass():
    s = SocraticStrategy()
    passed, feedback = s.should_pass("很好！[PASS]", 1, 5, None)
    assert passed is True


@pytest.mark.asyncio
async def test_socratic_continue():
    s = SocraticStrategy()
    passed, feedback = s.should_pass("你能举个例子吗？", 1, 5, None)
    assert passed is None


@pytest.mark.asyncio
async def test_feynman_opening():
    s = FeynmanStrategy()
    msg = s.get_opening_message("变量", "内容", None)
    assert "12" in msg


@pytest.mark.asyncio
async def test_adaptive_selects_scaffold_for_novice(novice):
    s = AdaptiveStrategy()
    inner = s._select_strategy(novice)
    assert isinstance(inner, ScaffoldStrategy)


@pytest.mark.asyncio
async def test_adaptive_selects_feynman_for_expert(expert):
    s = AdaptiveStrategy()
    inner = s._select_strategy(expert)
    assert isinstance(inner, FeynmanStrategy)


@pytest.mark.asyncio
async def test_adaptive_selects_socratic_default():
    s = AdaptiveStrategy()
    learner = LearnerProfile(user_id=3, knowledge_level=0.5, confidence=0.6)
    inner = s._select_strategy(learner)
    assert isinstance(inner, SocraticStrategy)


def test_get_strategy():
    s = get_strategy("socratic")
    assert isinstance(s, SocraticStrategy)
    s2 = get_strategy("unknown")
    assert isinstance(s2, AdaptiveStrategy)


@pytest.mark.asyncio
async def test_force_verdict_in_prompt(novice):
    session = Session(user_id=1, cartridge_id="py", current_node="N01", max_turns=2)
    session.add_exchange("user", "a1")
    session.add_exchange("user", "a2")
    s = SocraticStrategy()
    prompt = await s.build_system_prompt("内容", "标准", novice, session)
    assert "最后一轮" in prompt
