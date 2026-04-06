"""Tests for the Web API adapter."""
import pytest
from starlight.adapters.web_api import _parse_question


def test_parse_question_no_question():
    text = "Hello, this is a normal message"
    display, options, is_multi = _parse_question(text)
    assert display == text
    assert options == []
    assert is_multi is False


def test_parse_question_with_bracket_format():
    text = """来考考你
[QUESTION]
什么是变量？
[A] 存数据的盒子
[B] 一种函数
[C] 循环语句
[D] 文件路径
[/QUESTION]"""
    display, options, is_multi = _parse_question(text)
    assert "什么是变量" in display
    assert len(options) == 4
    assert options[0] == ("A", "存数据的盒子")
    assert options[3] == ("D", "文件路径")
    assert is_multi is False


def test_parse_question_with_dot_format():
    text = """[QUESTION]
Python 中 type() 的作用是？
A. 查看类型
B. 创建类
C. 删除对象
[/QUESTION]"""
    display, options, is_multi = _parse_question(text)
    assert len(options) == 3
    assert options[0] == ("A", "查看类型")


def test_parse_question_multi_select():
    text = """来考考你
[MULTI]
[QUESTION]
哪些是 Python 内置类型？
[A] int
[B] str
[C] MyCustomClass
[D] list
[/QUESTION]"""
    display, options, is_multi = _parse_question(text)
    assert is_multi is True
    assert len(options) == 4


def test_parse_question_no_close_tag():
    text = """考考你：
[QUESTION]
什么是函数？
[A] 可复用代码块
[B] 变量"""
    display, options, is_multi = _parse_question(text)
    assert len(options) == 2


def test_parse_question_with_trailing_parens():
    text = """[QUESTION]
选择正确答案
[A] 正确（提示：想想定义）
[B] 错误
[/QUESTION]"""
    display, options, is_multi = _parse_question(text)
    assert options[0] == ("A", "正确")
