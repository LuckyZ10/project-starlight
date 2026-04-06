"""Web API adapter — FastAPI + WebSocket for Claude.ai-style web frontend."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlight.adapters.base import HarnessResult
from starlight import database as db

logger = logging.getLogger(__name__)

router = APIRouter()

# Static HTML directory
WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"

# In-memory session-to-user mapping (Web → harness user_id)
_web_users: dict[str, int] = {}


@router.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web frontend."""
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@router.get("/manifest.json")
async def manifest():
    from fastapi.responses import JSONResponse
    data = json.loads((WEB_DIR / "manifest.json").read_text())
    return JSONResponse(content=data)


@router.get("/sw.js")
async def service_worker():
    from fastapi.responses import Response
    content = (WEB_DIR / "sw.js").read_text()
    return Response(content=content, media_type="application/javascript")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with the learning engine."""
    await websocket.accept()

    # Get or create user session
    session_id = str(uuid.uuid4())
    harness = websocket.app.state.harness

    # Temp user for web — in production, this would be auth
    user_id = await _ensure_web_user(session_id)
    cartridge_id: str | None = None

    try:
        # Send welcome
        await _send(websocket, {
            "type": "welcome",
            "text": "🌟 欢迎来到星光学习机！选择一个卡带开始学习吧。",
            "state": "idle",
        })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=120)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await _send(websocket, {"type": "heartbeat"})
                continue

            msg = json.loads(data)
            action = msg.get("action", "message")
            text = msg.get("text", "")

            if action == "browse":
                # Send structured cartridge list for interactive cards
                cartridges = []
                for cart_id in harness.cartridges.list_cartridges():
                    try:
                        cart = harness.cartridges.load(cart_id)
                        cartridges.append({
                            "id": cart_id,
                            "title": cart.get("title", cart_id),
                            "nodes": len(cart.get("nodes", [])),
                        })
                    except Exception:
                        cartridges.append({"id": cart_id, "title": cart_id, "nodes": 0})
                await _send(websocket, {
                    "type": "browse",
                    "cartridges": cartridges,
                    "state": "idle",
                })

            elif action == "start":
                cart_id = msg.get("cartridge_id", "")
                cartridge_id = cart_id
                await _send(websocket, {"type": "typing"})
                try:
                    result = await asyncio.wait_for(
                        harness.process(user_id=user_id, message="/start", cartridge_id=cart_id),
                        timeout=30,
                    )
                    await _send_result(websocket, result)
                except asyncio.TimeoutError:
                    await _send(websocket, {
                        "type": "message",
                        "text": "⏱️ AI 老师思考太久了，请再试一次",
                        "options": [],
                        "is_multi": False,
                        "verdict": None,
                        "state": "idle",
                    })

            elif action == "progress":
                result = await harness.process(
                    user_id=user_id, message="/progress", cartridge_id=cartridge_id,
                )
                await _send(websocket, {
                    "type": "progress",
                    "text": result.text,
                    "state": result.state,
                })

            elif action == "stats":
                result = await harness.process(user_id=user_id, message="/stats")
                await _send(websocket, {
                    "type": "stats",
                    "text": result.text,
                    "state": result.state,
                })

            elif action == "review":
                result = await harness.process(
                    user_id=user_id, message="/review", cartridge_id=cartridge_id,
                )
                await _send(websocket, {
                    "type": "review",
                    "text": result.text,
                    "state": result.state,
                })

            elif action == "message":
                if not text.strip():
                    continue
                # Show typing indicator
                await _send(websocket, {"type": "typing"})
                try:
                    result = await asyncio.wait_for(
                        harness.process(user_id=user_id, message=text, cartridge_id=cartridge_id),
                        timeout=30,
                    )
                    await _send_result(websocket, result)
                except asyncio.TimeoutError:
                    await _send(websocket, {
                        "type": "message",
                        "text": "⏱️ AI 老师思考太久了，请再试一次",
                        "options": [],
                        "is_multi": False,
                        "verdict": None,
                        "state": "learning",
                    })

    except WebSocketDisconnect:
        logger.info("Web client disconnected: %s", session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await _send(websocket, {"type": "error", "text": str(e)})
        except Exception:
            pass


async def _ensure_web_user(session_id: str) -> int:
    """Create or retrieve a user ID for a web session."""
    if session_id in _web_users:
        return _web_users[session_id]
    user_id = await db.ensure_user(
        telegram_id=hash(f"web:{session_id}") % (10**9),
        name=f"Web User",
    )
    _web_users[session_id] = user_id
    return user_id


async def _send(websocket: WebSocket, data: dict) -> None:
    """Send JSON to the websocket client."""
    await websocket.send_text(json.dumps(data, ensure_ascii=False))


async def _send_result(websocket: WebSocket, result: HarnessResult) -> None:
    """Send a HarnessResult to the websocket, parsing questions."""
    display, options, is_multi = _parse_question(result.text)
    await _send(websocket, {
        "type": "message",
        "text": display,
        "options": options,
        "is_multi": is_multi,
        "verdict": result.verdict,
        "state": result.state,
    })


# Re-use question parsing from telegram_adapter
def _parse_question(text: str) -> tuple[str, list[tuple[str, str]], bool]:
    """Parse [QUESTION]...[/QUESTION] from LLM response."""
    import re
    is_multi = bool(re.search(r'\[MULTI\]', text))
    match = re.search(r'\[QUESTION\](.*?)(?:\[/QUESTION\]|\[QUESTION\]|$)', text, re.DOTALL)
    if not match:
        return text, [], False

    block = match.group(1).strip()
    block = re.sub(r'\[/?MULTI\]', '', block).strip()

    option_re = re.compile(
        r'(?:\[([A-D])\]\s*|([A-D])[.、)\s])\s*(.+?)(?=\s*(?:\[[A-D]\]|[A-D][.、)\s])|$)',
        re.DOTALL,
    )
    options = []
    for m in option_re.finditer(block):
        label = m.group(1) or m.group(2)
        opt_text = m.group(3).strip()
        if label and opt_text:
            opt_text = re.sub(r'\[/?QUESTION\]', '', opt_text).strip()
            button_text = opt_text.split('\n')[0].strip()
            button_text = re.sub(r'\s*[（(].*$', '', button_text).strip()
            if button_text:
                options.append((label, button_text))

    first_opt = re.search(r'(?:\[[A-D]\]|[A-D][.、)\s])', block)
    q_text = block[:first_opt.start()].strip() if first_opt else block

    before = text[:text.find('[QUESTION]')].strip()
    before = re.sub(r'\[/?MULTI\]', '', before).strip()
    end_match = re.search(r'\[/QUESTION\]', text)
    after = text[end_match.end():].strip() if end_match else ""

    parts = [p for p in [before, q_text, after] if p]
    full_display = '\n\n'.join(parts)

    return full_display, options, is_multi
