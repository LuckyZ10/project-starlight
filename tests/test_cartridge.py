import pytest
from starlight.core.cartridge import CartridgeLoader

def test_load_cartridge():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    assert cart["id"] == "python-basics"
    assert len(cart["nodes"]) == 10
    assert cart["dag"]["entry"] == "N01"

def test_load_node_content():
    loader = CartridgeLoader("./cartridges")
    content = loader.load_node_content("python-basics", "nodes/N01-variables.md")
    assert "变量" in content
    assert len(content) > 50

def test_load_nonexistent_cartridge():
    loader = CartridgeLoader("./cartridges")
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent")

def test_get_entry_node():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    entry = loader.get_entry_node(cart)
    assert entry["id"] == "N01"
    assert entry["prerequisites"] == []

def test_get_next_nodes():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    next_nodes = loader.get_next_nodes(cart, "N01")
    assert len(next_nodes) == 1
    assert next_nodes[0]["id"] == "N02"

def test_list_cartridges():
    loader = CartridgeLoader("./cartridges")
    carts = loader.list_cartridges()
    assert "python-basics" in carts

def test_get_node_by_id():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    node = loader.get_node_by_id(cart, "N02")
    assert node["title"] == "数据类型"
    assert "N01" in node["prerequisites"]
