import json
from pathlib import Path
from typing import Any


class CartridgeLoader:
    def __init__(self, cartridges_dir: str):
        self.base_dir = Path(cartridges_dir)

    def load(self, cartridge_id: str) -> dict[str, Any]:
        manifest_path = self.base_dir / cartridge_id / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Cartridge not found: {cartridge_id}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_node_content(self, cartridge_id: str, node_file: str) -> str:
        path = self.base_dir / cartridge_id / node_file
        if not path.exists():
            raise FileNotFoundError(f"Node file not found: {node_file}")
        return path.read_text(encoding="utf-8")

    def get_entry_node(self, cartridge: dict) -> dict:
        entry_id = cartridge["dag"]["entry"]
        for node in cartridge["nodes"]:
            if node["id"] == entry_id:
                return node
        raise ValueError(f"Entry node {entry_id} not found in nodes")

    def get_next_nodes(self, cartridge: dict, current_node_id: str) -> list[dict]:
        edges = cartridge["dag"].get("edges", {})
        next_ids = edges.get(current_node_id, [])
        return [n for n in cartridge["nodes"] if n["id"] in next_ids]

    def get_node_by_id(self, cartridge: dict, node_id: str) -> dict:
        for node in cartridge["nodes"]:
            if node["id"] == node_id:
                return node
        raise ValueError(f"Node {node_id} not found")

    def list_cartridges(self) -> list[str]:
        return [
            d.name
            for d in self.base_dir.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ]
