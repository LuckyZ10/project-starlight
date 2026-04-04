#!/usr/bin/env python3
"""Start the Starlight Telegram Bot.

Usage:
    STARLIGHT_BOT_TOKEN=your-token python run_bot.py

Set environment variables with the STARLIGHT_ prefix to configure
(see starlight/config.py for all options).
"""
import asyncio
import logging
import sys

from starlight.config import settings
from starlight.adapters.telegram_adapter import TelegramAdapter
from starlight.core.cartridge import CartridgeLoader
from starlight.core.assessor_v2 import AssessorV2
from starlight.core.contributor import TributeEngine
from starlight.core.harness_v2 import LearningHarnessV2
from starlight.core.strategies import get_strategy
from starlight.core.progress import ProgressManager
from starlight.database import init_db, async_session

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def create_harness() -> LearningHarnessV2:
    """Build a fully-wired LearningHarnessV2 with adaptive strategy and real DB."""
    loader = CartridgeLoader(settings.cartridges_dir)
    strategy = get_strategy("adaptive")
    assessor = AssessorV2(
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        llm_base_url=getattr(settings, 'llm_base_url', ''),
        strategy=strategy,
    )
    session = async_session()
    progress_mgr = ProgressManager(session)
    tribute = TributeEngine()
    return LearningHarnessV2(
        cartridge_loader=loader,
        assessor=assessor,
        progress_mgr=progress_mgr,
        tribute_engine=tribute,
        strategy_name="adaptive",
    )


async def main() -> None:
    if not settings.bot_token:
        logger.error(
            "STARLIGHT_BOT_TOKEN is not set. "
            "Export it as an environment variable before running."
        )
        sys.exit(1)

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    adapter = TelegramAdapter(
        harness_factory=create_harness,
        bot_token=settings.bot_token,
    )

    logger.info("Starting Starlight Bot (mode=%s)…", settings.bot_mode)
    await adapter.start(mode=settings.bot_mode)

    # Block until interrupted
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down…")
        await adapter.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
