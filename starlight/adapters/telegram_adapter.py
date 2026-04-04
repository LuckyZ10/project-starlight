"""Telegram Bot adapter for the Starlight learning engine (V2)."""
from __future__ import annotations

import logging
from typing import Callable, Awaitable

from starlight.adapters.base import BaseAdapter, HarnessResult
from starlight.database import ensure_user, get_active_cartridge

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseAdapter):
    """Telegram Bot adapter for Starlight V2."""

    def __init__(self, harness_factory: Callable[[], Awaitable], bot_token: str):
        self._harness_factory = harness_factory
        self._bot_token = bot_token
        self._bot = None
        self._application = None
        self._harness = None

    async def send_message(self, user_id: str, text: str) -> None:
        if self._bot:
            await self._bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

    async def start(self, mode: str = "polling") -> None:
        from telegram import Update
        from telegram.ext import (
            ApplicationBuilder, CommandHandler, MessageHandler, filters,
        )

        self._application = (
            ApplicationBuilder().token(self._bot_token).build()
        )

        self._application.add_handler(CommandHandler("start", self._handle_start))
        self._application.add_handler(CommandHandler("browse", self._handle_browse))
        self._application.add_handler(CommandHandler("progress", self._handle_progress))
        self._application.add_handler(CommandHandler("help", self._handle_help))
        self._application.add_handler(CommandHandler("stats", self._handle_stats))
        self._application.add_handler(CommandHandler("review", self._handle_review))
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
            logger.info("Telegram bot initialized (webhook mode requires manual setup)")

    async def shutdown(self) -> None:
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()

    async def _get_harness(self):
        if self._harness is None:
            self._harness = await self._harness_factory()
        return self._harness

    async def _handle_start(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = context.args[0] if context.args else None

        if not cartridge_id:
            # Check if user has an active cartridge to resume
            active = await get_active_cartridge(telegram_id)
            if active:
                await update.message.reply_text(
                    f"🌟 欢迎回来！你正在学习 `{active}`\n\n"
                    "继续回答上一题，或用 /progress 查看进度"
                )
            else:
                await update.message.reply_text(
                    "🌟 欢迎来到星光学习机！\n\n"
                    "用 /browse 查看可用卡带\n"
                    "用 /start <卡带ID> 开始学习"
                )
            return

        result = await harness.process(user_id=user_id, message="/start", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)

    async def _handle_browse(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/browse")
        await update.message.reply_text(result.text)

    async def _handle_progress(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)
        result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)

    async def _handle_stats(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/stats")
        await update.message.reply_text(result.text)

    async def _handle_review(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)
        result = await harness.process(user_id=user_id, message="/review", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)

    async def _handle_help(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/help")
        await update.message.reply_text(result.text)

    async def _handle_message(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        text = update.message.text
        cartridge_id = await get_active_cartridge(telegram_id)

        if not cartridge_id:
            await update.message.reply_text("请先 /start 选择一个卡带开始学习。")
            return

        result = await harness.process(user_id=user_id, message=text, cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)
