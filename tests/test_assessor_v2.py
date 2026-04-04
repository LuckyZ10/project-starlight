# tests/test_assessor_v2.py
import pytest
from unittest.mock import AsyncMock
from starlight.core.assessor_v2 import AssessorV2, AssessmentResult
from starlight.core.strategies import SocraticStrategy
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile


@pytest.fixture
def assessor():
    a = AssessorV2(llm_model="test", llm_api_key="test", strategy=SocraticStrategy())
    a._call_llm = AsyncMock()
    return a


@pytest.fixture
def session():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("user", "变量是存东西的")
    return s


@pytest.fixture
def learner():
    return LearnerProfile(user_id=1)


@pytest.mark.asyncio
async def test_pass(assessor, session, learner):
    assessor._call_llm.return_value = "非常好，你理解了变量赋值！[PASS]"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "PASS"
    assert result.score > 0
    assert result.quality >= 4


@pytest.mark.asyncio
async def test_fail(assessor, session, learner):
    assessor._call_llm.return_value = "还需要再想想。[FAIL] 建议：注意赋值的语法。"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "FAIL"
    assert result.hint is not None
    assert result.error_type is not None


@pytest.mark.asyncio
async def test_continue(assessor, session, learner):
    assessor._call_llm.return_value = "你能举个具体的例子吗？"
    result = await assessor.assess("变量内容", "能写赋值语句", session, learner)
    assert result.verdict == "CONTINUE"
