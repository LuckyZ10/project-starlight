"""Telegram Bot adapter for the Starlight learning engine."""
from __future__ import annotations

import logging
from typing import Callable, Awaitable

from starlight.adapters.base import BaseAdapter, HarnessResult

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseAdapter):
    """Telegram Bot adapter for Starlight.

    Receives user messages via the Telegram Bot API, delegates processing
    to a LearningHarness obtained through *harness_factory*, and sends
    the result back to the chat.
    """

    def __init__(
        self,
        harness_factory: Callable[[], Awaitable],
        bot_token: str,
    ):
        """
        Args:
            harness_factory: async callable that returns a LearningHarness instance.
            bot_token: Telegram Bot API token.
        """
        self._harness_factory = harness_factory
        self._bot_token = bot_token
        self._bot = None
        self._application = None
        # user_id → cartridge_id  (production: persisted via ProgressManager)
        self._user_cartridges: dict[int, str] = {}

    # ------------------------------------------------------------------
    # BaseAdapter interface
    # ------------------------------------------------------------------

    async def send_message(self, user_id: str, text: str) -> None:
        """Send a message to a Telegram user."""
        if self._bot:
            await self._bot.send_message(
                chat_id=user_id, text=text, parse_mode="Markdown"
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, mode: str = "polling") -> None:
        """Start the bot in *polling* or *webhook* mode."""
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            filters,
        )

        self._application = (
            ApplicationBuilder().token(self._bot_token).build()
        )

        # Register command handlers
        self._application.add_handler(
            CommandHandler("start", self._handle_start)
        )
        self._application.add_handler(
            CommandHandler("browse", self._handle_browse)
        )
        self._application.add_handler(
            CommandHandler("progress", self._handle_progress)
        )
        self._application.add_handler(
            CommandHandler("help", self._handle_help)
        )

        # Free-text messages are treated as assessment answers
        self._application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        self._bot = self._application.bot

        if mode == "polling":
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling()
            logger.info("Telegram bot started in polling mode")
        else:
            logger.info(
                "Telegram bot initialized (webhook mode requires manual setup)"
            )

    async def shutdown(self) -> None:
        """Shut down the bot gracefully."""
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_harness(self):
        """Obtain a fresh harness from the factory."""
        return await self._harness_factory()

    # ------------------------------------------------------------------
    # Command handlers (called by python-telegram-bot)
    # ------------------------------------------------------------------

    async def _handle_start(self, update, context) -> None:
        """Handle ``/start [<cartridge_id>]``."""
        harness = await self._get_harness()
        user_id = update.effective_user.id
        cartridge_id = context.args[0] if context.args else None

        if not cartridge_id:
            await update.message.reply_text(
                "🌟 欢迎来到星光学习机！\n\n"
                "用 /browse 查看可用卡带\n"
                "用 /start <卡带ID> 开始学习"
            )
            return

        self._user_cartridges[user_id] = cartridge_id
        result = await harness.process(
            user_id=user_id, message="/start", cartridge_id=cartridge_id
        )
        await update.message.reply_text(result.text)

    async def _handle_browse(self, update, context) -> None:
        """Handle ``/browse``."""
        harness = await self._get_harness()
        result = await harness.process(
            user_id=update.effective_user.id, message="/browse"
        )
        await update.message.reply_text(result.text)

    async def _handle_progress(self, update, context) -> None:
        """Handle ``/progress``."""
        harness = await self._get_harness()
        user_id = update.effective_user.id
        cartridge_id = self._user_cartridges.get(user_id)
        result = await harness.process(
            user_id=user_id, message="/progress", cartridge_id=cartridge_id
        )
        await update.message.reply_text(result.text)

    async def _handle_help(self, update, context) -> None:
        """Handle ``/help``."""
        harness = await self._get_harness()
        result = await harness.process(
            user_id=update.effective_user.id, message="/help"
        )
        await update.message.reply_text(result.text)

    async def _handle_message(self, update, context) -> None:
        """Handle free-text messages as assessment answers."""
        harness = await self._get_harness()
        user_id = update.effective_user.id
        text = update.message.text
        cartridge_id = self._user_cartridges.get(user_id)

        if not cartridge_id:
            await update.message.reply_text(
                "请先用 /start <卡带ID> 选择一个卡带开始学习。"
            )
            return

        result = await harness.process(
            user_id=user_id, message=text, cartridge_id=cartridge_id
        )
        await update.message.reply_text(result.text)
