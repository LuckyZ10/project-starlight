import pytest
from starlight.core.assessor import Assessor, AssessmentResult

def async_lambda(text):
    """Helper: returns an async function that returns the given text (mock LLM)."""
    async def _mock(messages):
        return text
    return _mock

def test_build_system_prompt():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    prompt = assessor._build_system_prompt(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值",
        max_turns=3,
    )
    assert "星光学习机" in prompt
    assert "[PASS]" in prompt
    assert "[FAIL]" in prompt
    assert "变量是存储数据的容器" in prompt
    assert "3" in prompt

@pytest.mark.asyncio
async def test_assessor_returns_pass():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("基于你的回答，你已经理解了变量赋值的核心概念。[PASS]")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="变量就像一个盒子，可以把数据放进去。比如 name = 'hello' 就是把 hello 放进 name 这个盒子里。",
    )
    assert result.verdict == "PASS"
    assert result.score > 0

@pytest.mark.asyncio
async def test_assessor_returns_fail():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("你的回答还不够深入。[FAIL] 建议思考赋值和等于号的区别。")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="不知道",
    )
    assert result.verdict == "FAIL"
    assert result.hint is not None

@pytest.mark.asyncio
async def test_assessor_returns_continue():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("你提到了变量，但能更具体地说明赋值的语法吗？")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="变量就是存东西的",
    )
    assert result.verdict == "CONTINUE"

@pytest.mark.asyncio
async def test_assessor_with_conversation_history():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("很好，这次你展示了实际代码。[PASS]")
    conversation = [
        {"role": "assistant", "content": "能写一段赋值代码吗？"},
        {"role": "user", "content": "x = 10"},
    ]
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能写赋值语句",
        conversation=conversation,
        user_answer="是的，x = 10 就是把 10 赋给 x。",
    )
    assert result.verdict == "PASS"

def test_parse_pass_with_score():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    result = assessor._parse_response("非常好！完全理解。[PASS]")
    assert result.verdict == "PASS"
    assert result.score >= 90

def test_parse_pass_normal():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    result = assessor._parse_response("理解了基本概念。[PASS]")
    assert result.verdict == "PASS"
    assert result.score >= 70

def test_parse_fail_with_hint():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    result = assessor._parse_response("还不够。[FAIL] 建议：思考赋值的语法结构。")
    assert result.verdict == "FAIL"
    assert result.hint is not None
    assert "赋值" in result.hint

def test_parse_fail_no_hint():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    result = assessor._parse_response("[FAIL]")
    assert result.verdict == "FAIL"
    assert result.hint is not None  # should get default hint

def test_parse_continue():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    result = assessor._parse_response("能再详细说明一下吗？")
    assert result.verdict == "CONTINUE"
