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
from starlight.core.assessor import Assessor
from starlight.core.contributor import TributeEngine
from starlight.core.harness import LearningHarness
from starlight.main import MockProgressManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def create_harness() -> LearningHarness:
    """Build a fully-wired LearningHarness."""
    loader = CartridgeLoader(settings.cartridges_dir)
    assessor = Assessor(
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        max_turns=settings.assessment_max_turns,
    )
    progress_mgr = MockProgressManager()
    tribute = TributeEngine()
    return LearningHarness(loader, assessor, progress_mgr, tribute)


async def main() -> None:
    if not settings.bot_token:
        logger.error(
            "STARLIGHT_BOT_TOKEN is not set. "
            "Export it as an environment variable before running."
        )
        sys.exit(1)

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
