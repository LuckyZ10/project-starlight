"""Cartridge and node endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path as FPath
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import LearningProgress, User
from auth import get_current_user_optional

router = APIRouter(prefix="/api/cartridges", tags=["cartridges"])

CARTRIDGES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "cartridges"


@router.get("")
async def list_cartridges():
    """List all available cartridges."""
    results = []
    if not CARTRIDGES_DIR.exists():
        return results
    for d in sorted(CARTRIDGES_DIR.iterdir()):
        manifest_path = d / "manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                results.append({
                    "id": data.get("id", d.name),
                    "title": data.get("title", d.name),
                    "version": data.get("version", "1.0.0"),
                    "node_count": len(data.get("nodes", [])),
                })
            except Exception:
                pass
    return results


@router.get("/{cartridge_id}")
async def get_cartridge(
    cartridge_id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Get cartridge detail with optional progress."""
    cdir = CARTRIDGES_DIR / cartridge_id
    manifest_path = cdir / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(404, "Cartridge not found")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Build nodes with progress
    nodes = []
    completed = 0
    for n in data.get("nodes", []):
        status = "not_started"
        score = None
        if user:
            stmt = select(LearningProgress).where(
                LearningProgress.user_id == user.id,
                LearningProgress.cartridge_id == cartridge_id,
                LearningProgress.node_id == n["id"],
            )
            result = await db.execute(stmt)
            prog = result.scalar_one_or_none()
            if prog:
                status = prog.status
                score = prog.score
        if status == "completed":
            completed += 1
        nodes.append({
            "id": n["id"],
            "title": n["title"],
            "difficulty": n.get("difficulty", 3),
            "prerequisites": n.get("prerequisites", []),
            "pass_criteria": n.get("pass_criteria", ""),
            "status": status,
            "score": score,
        })

    return {
        "id": data.get("id", cartridge_id),
        "title": data.get("title", cartridge_id),
        "version": data.get("version", "1.0.0"),
        "nodes": nodes,
        "progress": {"completed": completed, "total": len(nodes)},
        "dag": data.get("dag", {}),
    }


@router.get("/{cartridge_id}/nodes/{node_id}")
async def get_node_content(cartridge_id: str, node_id: str):
    """Read a node's .md content."""
    nodes_dir = CARTRIDGES_DIR / cartridge_id / "nodes"
    if not nodes_dir.exists():
        raise HTTPException(404, "Nodes directory not found")

    # Find file matching node_id prefix (e.g., N01-xxx.md)
    for f in nodes_dir.iterdir():
        if f.name.startswith(node_id) and f.suffix == ".md":
            return {
                "id": node_id,
                "title": f.stem.split("-", 1)[-1] if "-" in f.stem else f.stem,
                "content": f.read_text(encoding="utf-8"),
            }

    raise HTTPException(404, f"Node {node_id} not found")
