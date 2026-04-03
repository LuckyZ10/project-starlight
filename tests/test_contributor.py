from starlight.core.contributor import TributeEngine

def test_build_node_tribute():
    engine = TributeEngine()
    contributor = {"name": "张轶霖", "github": "LuckyZ10", "quote": "从零开始"}
    text = engine.build_node_tribute("N01", "变量与赋值", contributor)
    assert "张轶霖" in text
    assert "变量与赋值" in text
    assert "从零开始" in text

def test_build_completion_tribute():
    engine = TributeEngine()
    contributors = [
        {"name": "张轶霖", "github": "LuckyZ10", "quote": "从零开始", "role": "author"},
        {"name": "小明", "github": "xiaoming", "quote": "学习使我快乐", "role": "reviewer"},
    ]
    text = engine.build_completion_tribute("python-basics", "Python 基础", contributors, learner_count=42)
    assert "Python 基础" in text
    assert "张轶霖" in text
    assert "小明" in text
    assert "42" in text

def test_build_completion_tribute_first_learner():
    engine = TributeEngine()
    text = engine.build_completion_tribute("python-basics", "Python", [], learner_count=1)
    assert "第 1 位" in text or "第一位" in text
