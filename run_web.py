#!/usr/bin/env python3
"""Start the Starlight Web Server (Claude.ai-style interface).

Usage:
    python run_web.py [--port 8000] [--host 0.0.0.0]

Set environment variables with the STARLIGHT_ prefix to configure
(see starlight/config.py for all options).
"""
import argparse
import asyncio
import logging
import sys

import uvicorn

from starlight.config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_app():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path

    from starlight.core.cartridge import CartridgeLoader
    from starlight.core.assessor_v2 import AssessorV2
    from starlight.core.contributor import TributeEngine
    from starlight.core.harness_v2 import LearningHarnessV2
    from starlight.core.strategies import get_strategy
    from starlight.database import DatabaseProgressManager, init_db
    from starlight.adapters.web_api import router

    app = FastAPI(title="星光学习机", version="2.0.0")

    # Wire up harness on startup
    @app.on_event("startup")
    async def startup():
        await init_db()
        loader = CartridgeLoader(settings.cartridges_dir)
        strategy = get_strategy("adaptive")
        assessor = AssessorV2(
            llm_model=settings.llm_model,
            llm_api_key=settings.llm_api_key,
            llm_base_url=getattr(settings, 'llm_base_url', ''),
            strategy=strategy,
        )
        progress_mgr = DatabaseProgressManager()
        tribute = TributeEngine()
        harness = LearningHarnessV2(
            cartridge_loader=loader,
            assessor=assessor,
            progress_mgr=progress_mgr,
            tribute_engine=tribute,
            strategy_name="adaptive",
        )
        app.state.harness = harness
        logger.info("✨ Starlight Web server ready — harness initialized")

    # Web routes (WebSocket + HTML)
    app.include_router(router)

    # Health check
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "2.0.0"}

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Starlight Web Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for dev")
    args = parser.parse_args()

    if args.reload:
        uvicorn.run(
            "run_web:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=["starlight", "web"],
        )
    else:
        app = create_app()
        uvicorn.run(app, host=args.host, port=args.port)
