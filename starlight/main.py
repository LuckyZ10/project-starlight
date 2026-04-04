# starlight/main.py
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace

from fastapi import FastAPI, Request
from starlight.config import settings

# Will be populated in lifespan / telegram adapter task
_bot = None
_harness = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot, _harness
    from starlight.core.cartridge import CartridgeLoader
    from starlight.core.assessor import Assessor
    from starlight.core.contributor import TributeEngine
    from starlight.core.harness import LearningHarness

    loader = CartridgeLoader(settings.cartridges_dir)
    assessor = Assessor(
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        max_turns=settings.assessment_max_turns,
    )
    # Note: progress_mgr uses in-memory mock for now; will be wired to DB in Phase 4
    progress_mgr = MockProgressManager()
    tribute = TributeEngine()
    _harness = LearningHarness(loader, assessor, progress_mgr, tribute)

    yield

    if _bot:
        await _bot.shutdown()


app = FastAPI(title="Starlight", version="0.1.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"name": "Starlight", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    """Webhook endpoint for Telegram Bot API."""
    if bot_token != settings.bot_token:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"error": "unauthorized"})
    update_data = await request.json()
    # Will be processed by telegram adapter in Task 4
    return {"ok": True}


class MockProgressManager:
    """In-memory progress manager for development/testing."""

    def __init__(self):
        self._progress: dict[tuple[int, str], SimpleNamespace] = {}

    async def get_progress(self, user_id: int, cartridge_id: str):
        return self._progress.get((user_id, cartridge_id))

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01"):
        p = SimpleNamespace(
            user_id=user_id,
            cartridge_id=cartridge_id,
            current_node=entry_node,
            status="in_progress",
        )
        self._progress[(user_id, cartridge_id)] = p
        return p

    async def advance_node(self, user_id: int, cartridge_id: str, next_node: str):
        p = await self.get_progress(user_id, cartridge_id)
        if p is None:
            raise ValueError(f"No progress found for user {user_id} in {cartridge_id}")
        p.current_node = next_node
        return p

    async def complete_cartridge(self, user_id: int, cartridge_id: str):
        p = await self.get_progress(user_id, cartridge_id)
        if p is None:
            raise ValueError("No progress found")
        p.status = "completed"
        p.completed_at = datetime.utcnow()
        return p
