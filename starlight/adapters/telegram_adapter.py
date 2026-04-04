"""Telegram Bot adapter for the Starlight learning engine (V2)."""
from __future__ import annotations

import logging
from typing import Callable, Awaitable

from starlight.adapters.base import BaseAdapter, HarnessResult
from starlight.database import ensure_user, get_active_cartridge

logger = logging.getLogger(__name__)


def _main_menu_keyboard():
    """Default inline keyboard for main menu / idle state."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📚 浏览卡带", callback_data="/browse"),
            InlineKeyboardButton("📊 我的进度", callback_data="/progress"),
        ],
        [
            InlineKeyboardButton("❓ 帮助", callback_data="/help"),
        ],
    ])


def _learning_keyboard():
    """Inline keyboard shown during active learning."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 进度", callback_data="/progress"),
            InlineKeyboardButton("🎯 拉回正轨", callback_data="/back"),
        ],
        [
            InlineKeyboardButton("📚 换卡带", callback_data="/browse"),
            InlineKeyboardButton("❓ 帮助", callback_data="/help"),
        ],
    ])


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
            ApplicationBuilder, CommandHandler, MessageHandler,
            CallbackQueryHandler, filters,
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
        # Inline button callbacks
        self._application.add_handler(CallbackQueryHandler(self._handle_callback))

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

    # ------------------------------------------------------------------
    # Callback query handler (inline button clicks)
    # ------------------------------------------------------------------
    async def _handle_callback(self, update, context) -> None:
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()

        data = query.data
        telegram_id = query.from_user.id
        name = query.from_user.full_name or "Unknown"

        harness = await self._get_harness()
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)

        if data == "/browse":
            result = await harness.process(user_id=user_id, message="/browse")
            # Build cartridge buttons
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            from starlight.core.cartridge import CartridgeLoader
            from starlight.config import settings
            loader = CartridgeLoader(settings.cartridges_dir)
            buttons = []
            for cid in loader.list_cartridges():
                try:
                    cart = loader.load(cid)
                    buttons.append([InlineKeyboardButton(
                        f"🎮 {cart['title']}", callback_data=f"/start {cid}"
                    )])
                except Exception:
                    pass
            await query.edit_message_text(
                result.text,
                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
            )

        elif data.startswith("/start "):
            cart_id = data.split(" ", 1)[1]
            result = await harness.process(user_id=user_id, message="/start", cartridge_id=cart_id)
            await query.edit_message_text(
                result.text,
                reply_markup=_learning_keyboard() if result.state == "learning" else None,
            )

        elif data == "/progress":
            result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
            kb = _learning_keyboard() if cartridge_id else _main_menu_keyboard()
            await query.edit_message_text(result.text, reply_markup=kb)

        elif data == "/back":
            result = await harness.process(user_id=user_id, message="/back", cartridge_id=cartridge_id)
            await query.edit_message_text(
                result.text,
                reply_markup=_learning_keyboard(),
            )

        elif data == "/help":
            result = await harness.process(user_id=user_id, message="/help")
            await query.edit_message_text(result.text, reply_markup=_main_menu_keyboard())

        else:
            await query.edit_message_text("未知操作")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _handle_start(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = context.args[0] if context.args else None

        if not cartridge_id:
            active = await get_active_cartridge(telegram_id)
            if active:
                await update.message.reply_text(
                    f"🌟 欢迎回来！你正在学习 `{active}`\n\n继续回答上一题，或用 /progress 查看进度",
                    reply_markup=_learning_keyboard(),
                )
            else:
                await update.message.reply_text(
                    "🌟 欢迎来到星光学习机！\n\n选择一个卡带开始学习吧 👇",
                    reply_markup=_main_menu_keyboard(),
                )
            return

        result = await harness.process(user_id=user_id, message="/start", cartridge_id=cartridge_id)
        kb = _learning_keyboard() if result.state == "learning" else _main_menu_keyboard()
        await update.message.reply_text(result.text, reply_markup=kb)

    async def _handle_browse(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/browse")

        # Add cartridge selection buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from starlight.core.cartridge import CartridgeLoader
        from starlight.config import settings
        loader = CartridgeLoader(settings.cartridges_dir)
        buttons = []
        for cid in loader.list_cartridges():
            try:
                cart = loader.load(cid)
                buttons.append([InlineKeyboardButton(
                    f"🎮 {cart['title']}", callback_data=f"/start {cid}"
                )])
            except Exception:
                pass
        await update.message.reply_text(
            result.text,
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )

    async def _handle_progress(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)
        result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
        kb = _learning_keyboard() if cartridge_id else _main_menu_keyboard()
        await update.message.reply_text(result.text, reply_markup=kb)

    async def _handle_stats(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/stats")
        await update.message.reply_text(result.text, reply_markup=_main_menu_keyboard())

    async def _handle_review(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)
        result = await harness.process(user_id=user_id, message="/review", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text, reply_markup=_main_menu_keyboard())

    async def _handle_help(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/help")
        await update.message.reply_text(result.text, reply_markup=_main_menu_keyboard())

    async def _handle_message(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        text = update.message.text
        cartridge_id = await get_active_cartridge(telegram_id)

        if not cartridge_id:
            await update.message.reply_text(
                "请先选择一个卡带开始学习 👇",
                reply_markup=_main_menu_keyboard(),
            )
            return

        result = await harness.process(user_id=user_id, message=text, cartridge_id=cartridge_id)
        kb = _learning_keyboard() if result.state == "learning" else _main_menu_keyboard()
        await update.message.reply_text(result.text, reply_markup=kb)
