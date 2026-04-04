# tests/test_assessor_v2.py
import pytest
from unittest.mock import AsyncMock

from starlight.core.assessor_v2 import AssessorV2, AssessmentResult
from starlight.core.strategies import SocraticStrategy
from starlight.core.session import Session
from starlight.core.learner import LearnerProfile


@pytest.fixture
def assessor():
    a = AssessorV2(llm_model="test", llm_api_key="test",
                   strategy=SocraticStrategy())
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


@pytest.mark.asyncio
async def test_llm_base_url_passed():
    """Assessor V2 supports llm_base_url parameter"""
    a = AssessorV2(llm_model="test", llm_api_key="test",
                   llm_base_url="http://localhost:11434/v1",
                   strategy=SocraticStrategy())
    assert a.llm_base_url == "http://localhost:11434/v1"


@pytest.mark.asyncio
async def test_estimate_score_excellent(assessor, session, learner):
    assessor._call_llm.return_value = "优秀！完全理解了！[PASS]"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.score == 95
    assert result.quality == 5


@pytest.mark.asyncio
async def test_estimate_score_good(assessor, session, learner):
    assessor._call_llm.return_value = "很好，理解正确！[PASS]"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.score == 85
    assert result.quality == 4


@pytest.mark.asyncio
async def test_estimate_score_pass_default(assessor, session, learner):
    assessor._call_llm.return_value = "[PASS] 可以继续了"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.score == 75
    assert result.quality == 3


@pytest.mark.asyncio
async def test_error_classification_concept(assessor, session, learner):
    assessor._call_llm.return_value = "[FAIL] 你对概念和原理的理解有误"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.error_type == "concept"


@pytest.mark.asyncio
async def test_error_classification_application(assessor, session, learner):
    assessor._call_llm.return_value = "[FAIL] 你还无法应用到实际场景中"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.error_type == "application"


@pytest.mark.asyncio
async def test_error_classification_attention(assessor, session, learner):
    assessor._call_llm.return_value = "[FAIL] 注意细节"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.error_type == "attention"


@pytest.mark.asyncio
async def test_fail_hint_extraction(assessor, session, learner):
    assessor._call_llm.return_value = "[FAIL] 这还不对。\n建议：再想想变量的本质。"
    result = await assessor.assess("内容", "标准", session, learner)
    assert "建议" in result.hint


@pytest.mark.asyncio
async def test_fail_default_hint(assessor, session, learner):
    assessor._call_llm.return_value = "[FAIL] 不对。"
    result = await assessor.assess("内容", "标准", session, learner)
    assert result.hint == "再复习一下这个知识点，注意核心概念。"
