"""Telegram Bot adapter for the Starlight learning engine (V2)."""
from __future__ import annotations

import logging
import re
from typing import Callable, Awaitable

from starlight.adapters.base import BaseAdapter, HarnessResult
from starlight.database import ensure_user, get_active_cartridge

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inline Keyboard helpers
# ---------------------------------------------------------------------------

def _main_menu_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 浏览卡带", callback_data="/browse"),
         InlineKeyboardButton("📊 我的进度", callback_data="/progress")],
        [InlineKeyboardButton("❓ 帮助", callback_data="/help")],
    ])


def _learning_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 进度", callback_data="/progress"),
         InlineKeyboardButton("🎯 拉回正轨", callback_data="/back")],
        [InlineKeyboardButton("📚 换卡带", callback_data="/browse"),
         InlineKeyboardButton("❓ 帮助", callback_data="/help")],
    ])


def _parse_question(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Parse [QUESTION]...[/QUESTION] from LLM response.
    
    Returns (display_text, [(label, option_text), ...]).
    """
    match = re.search(r'\[QUESTION\](.*?)\[/QUESTION\]', text, re.DOTALL)
    if not match:
        return text, []

    block = match.group(1).strip()
    # Extract options [A] text
    option_re = re.compile(r'\[([A-D])\]\s*(.+?)(?=\s*\[[A-D]\]|$)', re.DOTALL)
    options = [(l, t.strip()) for l, t in option_re.findall(block)]

    # Question text = everything before first [A]
    first = block.find('[')
    q_text = block[:first].strip() if first > 0 else block

    # Build display
    lines = [q_text]
    for label, opt in options:
        lines.append(f"  {label}. {opt}")
    display = '\n'.join(lines)

    # Surrounding text (before/after the question block)
    before = text[:text.find('[QUESTION]')].strip()
    after = text[text.find('[/QUESTION]') + len('[/QUESTION]'):].strip()
    parts = [p for p in [before, display, after] if p]
    full_display = '\n\n'.join(parts)

    return full_display, options


def _options_keyboard(options):
    """Build inline keyboard from question options + free input."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for label, opt_text in options:
        buttons.append([InlineKeyboardButton(
            f"{label}. {opt_text}", callback_data=f"ANSWER:{label}"
        )])
    buttons.append([InlineKeyboardButton("✏️ 自己写", callback_data="ANSWER:FREE")])
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

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
    # Smart reply with question parsing
    # ------------------------------------------------------------------
    async def _reply(self, reply_func, result: HarnessResult,
                     cartridge_id: str | None = None) -> None:
        """Send reply with question buttons or standard keyboard."""
        display, options = _parse_question(result.text)
        if options:
            kb = _options_keyboard(options)
        elif result.state == "learning":
            kb = _learning_keyboard()
        else:
            kb = _main_menu_keyboard()
        try:
            await reply_func(display, reply_markup=kb)
        except Exception:
            try:
                await reply_func(display)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

    async def _reply_text(self, reply_func, text: str, state: str = "idle") -> None:
        """Simple reply with standard keyboard (no question parsing)."""
        kb = _learning_keyboard() if state == "learning" else _main_menu_keyboard()
        try:
            await reply_func(text, reply_markup=kb)
        except Exception:
            try:
                await reply_func(text)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

    # ------------------------------------------------------------------
    # Callback query (inline button clicks)
    # ------------------------------------------------------------------
    async def _handle_callback(self, update, context) -> None:
        query = update.callback_query
        await query.answer()

        data = query.data
        telegram_id = query.from_user.id
        name = query.from_user.full_name or "Unknown"

        harness = await self._get_harness()
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)

        # Answer button click — treat like a text message
        if data.startswith("ANSWER:"):
            answer = data.split(":", 1)[1]
            if answer == "FREE":
                await query.edit_message_text(
                    "✏️ 请直接输入你的回答：",
                    reply_markup=None,
                )
                return
            # Map label to full option text
            display, options = _parse_question("")
            # Get the option text for the label
            label_text = answer
            # Send the answer as a regular message to harness
            if not cartridge_id:
                await query.edit_message_text("请先选择一个卡带。")
                return
            result = await harness.process(user_id=user_id, message=answer, cartridge_id=cartridge_id)
            await self._reply(query.edit_message_text, result, cartridge_id)
            return

        if data == "/browse":
            result = await harness.process(user_id=user_id, message="/browse")
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
            await self._reply(query.edit_message_text, result, cart_id)

        elif data == "/progress":
            result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
            kb = _learning_keyboard() if cartridge_id else _main_menu_keyboard()
            await query.edit_message_text(result.text, reply_markup=kb)

        elif data == "/back":
            result = await harness.process(user_id=user_id, message="/back", cartridge_id=cartridge_id)
            await self._reply(query.edit_message_text, result, cartridge_id)

        elif data == "/help":
            result = await harness.process(user_id=user_id, message="/help")
            await query.edit_message_text(result.text, reply_markup=_main_menu_keyboard())

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
                await self._reply_text(
                    update.message.reply_text,
                    f"🌟 欢迎回来！你正在学习 `{active}`\n\n继续回答上一题，或用 /progress 查看进度",
                    state="learning",
                )
            else:
                await self._reply_text(
                    update.message.reply_text,
                    "🌟 欢迎来到星光学习机！\n\n选择一个卡带开始学习吧 👇",
                )
            return

        result = await harness.process(user_id=user_id, message="/start", cartridge_id=cartridge_id)
        await self._reply(update.message.reply_text, result, cartridge_id)

    async def _handle_browse(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/browse")

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
        state = "learning" if cartridge_id else "idle"
        await self._reply_text(update.message.reply_text, result.text, state=state)

    async def _handle_stats(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/stats")
        await self._reply_text(update.message.reply_text, result.text)

    async def _handle_review(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)
        result = await harness.process(user_id=user_id, message="/review", cartridge_id=cartridge_id)
        await self._reply_text(update.message.reply_text, result.text)

    async def _handle_help(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        result = await harness.process(user_id=user_id, message="/help")
        await self._reply_text(update.message.reply_text, result.text)

    async def _handle_message(self, update, context) -> None:
        harness = await self._get_harness()
        telegram_id = update.effective_user.id
        name = update.effective_user.full_name or "Unknown"
        user_id = await ensure_user(telegram_id, name)
        text = update.message.text
        cartridge_id = await get_active_cartridge(telegram_id)

        if not cartridge_id:
            await self._reply_text(
                update.message.reply_text,
                "请先选择一个卡带开始学习 👇",
            )
            return

        result = await harness.process(user_id=user_id, message=text, cartridge_id=cartridge_id)
        await self._reply(update.message.reply_text, result, cartridge_id)
