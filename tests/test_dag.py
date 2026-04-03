import pytest
from starlight.core.dag import DAGEngine

def test_get_unlocked_nodes_no_prerequisites():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
    ]
    completed = set()
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N01"

def test_get_unlocked_after_completing_n01():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
        {"id": "N03", "prerequisites": ["N02"]},
    ]
    completed = {"N01"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N02"

def test_all_unlocked():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
    ]
    completed = {"N01", "N02"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 0

def test_multiple_prerequisites():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": []},
        {"id": "N03", "prerequisites": ["N01", "N02"]},
    ]
    completed = {"N01"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N02"

def test_multiple_prerequisites_both_done():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": []},
        {"id": "N03", "prerequisites": ["N01", "N02"]},
    ]
    completed = {"N01", "N02"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N03"

def test_detect_cycle():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": ["N01"]}
    assert engine.has_cycle(edges) is True

def test_no_cycle():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": []}
    assert engine.has_cycle(edges) is False

def test_all_nodes_reachable():
    engine = DAGEngine()
    edges = {"N01": ["N02", "N03"], "N02": ["N04"], "N03": [], "N04": []}
    assert engine.all_reachable("N01", edges, 4) is True

def test_orphan_node_detected():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": [], "N03": []}
    assert engine.all_reachable("N01", edges, 3) is False

def test_get_learning_path():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": []}
    path = engine.get_learning_path("N01", edges)
    assert path == ["N01", "N02", "N03"]

def test_get_learning_path_branching():
    engine = DAGEngine()
    edges = {"N01": ["N02", "N03"], "N02": ["N04"], "N03": ["N04"], "N04": []}
    path = engine.get_learning_path("N01", edges)
    assert path[0] == "N01"
    assert path[-1] == "N04"
    assert len(path) == 4
