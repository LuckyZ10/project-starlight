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


def _parse_question(text: str) -> tuple[str, list[tuple[str, str]], bool]:
    """Parse [QUESTION]...[/QUESTION] from LLM response.

    Returns (display_text, [(label, option_text), ...], is_multi).
    Supports both [A] and A. option formats.
    Tolerates missing [/QUESTION] close tag.
    Detects [MULTI] tag for multi-select questions.
    """
    # Detect [MULTI] tag anywhere before or inside [QUESTION]
    is_multi = bool(re.search(r'\[MULTI\]', text))

    # Try proper close tag first, then tolerate missing/improper close
    match = re.search(r'\[QUESTION\](.*?)(?:\[/QUESTION\]|\[QUESTION\]|$)', text, re.DOTALL)
    if not match:
        return text, [], False

    block = match.group(1).strip()
    # Remove [MULTI] from block if present
    block = re.sub(r'\[/?MULTI\]', '', block).strip()

    # Extract options: [A] text OR A. text OR A、text
    option_re = re.compile(r'(?:\[([A-D])\]\s*|([A-D])[.、)\s])\s*(.+?)(?=\s*(?:\[[A-D]\]|[A-D][.、)\s])|$)', re.DOTALL)
    options = []
    trailing_text = ""
    for m in option_re.finditer(block):
        label = m.group(1) or m.group(2)
        opt_text = m.group(3).strip()
        if label and opt_text:
            # Clean up any stray tags from option text
            opt_text = re.sub(r'\[/?QUESTION\]', '', opt_text).strip()
            # Only keep the first line for button text
            lines = opt_text.split('\n')
            button_text = lines[0].strip()
            # Remove trailing parenthetical explanations (提示：...)
            button_text = re.sub(r'\s*[（(].*$', '', button_text).strip()
            # Keep any extra explanation for display
            extra = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ""
            if extra:
                trailing_text = extra
            if button_text:
                options.append((label, button_text))

    # Question text = everything before first option
    first_opt = re.search(r'(?:\[[A-D]\]|[A-D][.、)\s])', block)
    q_text = block[:first_opt.start()].strip() if first_opt else block

    # Build display — question text + any trailing hints (NOT options)
    display_parts = [q_text]
    if trailing_text:
        display_parts.append(f"💡 {trailing_text}")
    if is_multi:
        display_parts.append("☑️ 多选题 — 可选多个")
    display = '\n\n'.join(display_parts)

    # Surrounding text (before/after the question block)
    before = text[:text.find('[QUESTION]')].strip()
    # Clean [MULTI] from before text
    before = re.sub(r'\[/?MULTI\]', '', before).strip()
    end_match = re.search(r'\[/QUESTION\]', text)
    if end_match:
        after = text[end_match.end():].strip()
    else:
        after = ""
    parts = [p for p in [before, display, after] if p]
    full_display = '\n\n'.join(parts)

    return full_display, options, is_multi


def _options_keyboard(options, is_multi=False, selected=None):
    """Build inline keyboard from question options + free input.

    For multi-select: shows checkmarks on selected items + confirm button.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    selected = selected or set()
    buttons = []
    for label, opt_text in options:
        if is_multi:
            prefix = "✅ " if label in selected else "⬜ "
            buttons.append([InlineKeyboardButton(
                f"{prefix}{label}. {opt_text}",
                callback_data=f"MULTI:{label}",
            )])
        else:
            buttons.append([InlineKeyboardButton(
                f"{label}. {opt_text}", callback_data=f"ANSWER:{label}"
            )])

    if is_multi:
        if selected:
            buttons.append([InlineKeyboardButton(
                "✅ 确认提交", callback_data="MULTI:SUBMIT"
            )])
        buttons.append([InlineKeyboardButton("✏️ 自己写", callback_data="ANSWER:FREE")])
    else:
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
        # Multi-select state: {telegram_id: {message_id: {"selected": set, "options": list}}}
        self._multi_state: dict[int, dict[int, dict]] = {}

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

    def _save_multi_state(self, telegram_id: int, message_id: int,
                          options: list, selected: set | None = None):
        """Save multi-select state for a message."""
        if telegram_id not in self._multi_state:
            self._multi_state[telegram_id] = {}
        self._multi_state[telegram_id][message_id] = {
            "options": options,
            "selected": selected or set(),
        }

    def _get_multi_state(self, telegram_id: int, message_id: int) -> dict | None:
        """Get multi-select state for a message."""
        return self._multi_state.get(telegram_id, {}).get(message_id)

    def _clear_multi_state(self, telegram_id: int, message_id: int):
        """Clear multi-select state after submission."""
        if telegram_id in self._multi_state:
            self._multi_state[telegram_id].pop(message_id, None)

    # ------------------------------------------------------------------
    # Smart reply with question parsing
    # ------------------------------------------------------------------
    async def _reply(self, reply_func, result: HarnessResult,
                     cartridge_id: str | None = None,
                     telegram_id: int | None = None) -> None:
        """Send reply with question buttons or standard keyboard."""
        display, options, is_multi = _parse_question(result.text)
        logger.info("_reply: options=%d, is_multi=%s, has [QUESTION]=%s",
                     len(options), is_multi, "[QUESTION]" in result.text)
        if options:
            kb = _options_keyboard(options, is_multi=is_multi)
        elif result.state == "learning":
            kb = _learning_keyboard()
        else:
            kb = _main_menu_keyboard()
        try:
            msg = await reply_func(display, reply_markup=kb)
            # Save multi-select state if needed
            if options and is_multi and telegram_id and msg and msg.message_id:
                self._save_multi_state(telegram_id, msg.message_id, options)
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
        message_id = query.message.message_id if query.message else None

        harness = await self._get_harness()
        user_id = await ensure_user(telegram_id, name)
        cartridge_id = await get_active_cartridge(telegram_id)

        # --- Multi-select toggle ---
        if data.startswith("MULTI:"):
            action = data.split(":", 1)[1]
            if action == "SUBMIT":
                # Submit multi-select answers
                if not cartridge_id:
                    await query.edit_message_text("请先选择一个卡带。")
                    return
                state = self._get_multi_state(telegram_id, message_id) if message_id else None
                if not state or not state["selected"]:
                    await query.answer("请先选择至少一个选项", show_alert=True)
                    return
                # Build answer string from selected labels
                selected_labels = sorted(state["selected"])
                # Map labels to option texts
                label_map = {l: t for l, t in state["options"]}
                answer_parts = [f"{l}. {label_map.get(l, l)}" for l in selected_labels]
                answer = "、".join(selected_labels) + "（" + "、".join(answer_parts) + "）"
                self._clear_multi_state(telegram_id, message_id)
                result = await harness.process(user_id=user_id, message=answer, cartridge_id=cartridge_id)
                await self._reply(query.edit_message_text, result, cartridge_id, telegram_id)
                return
            else:
                # Toggle a selection
                label = action
                state = self._get_multi_state(telegram_id, message_id) if message_id else None
                if not state:
                    await query.answer("题目已过期，请重新开始", show_alert=True)
                    return
                if label in state["selected"]:
                    state["selected"].discard(label)
                else:
                    state["selected"].add(label)
                # Re-render keyboard with updated selections
                kb = _options_keyboard(state["options"], is_multi=True, selected=state["selected"])
                try:
                    await query.edit_message_reply_markup(reply_markup=kb)
                except Exception:
                    pass
                return

        # --- Single-select answer ---
        if data.startswith("ANSWER:"):
            answer = data.split(":", 1)[1]
            if answer == "FREE":
                await query.edit_message_text(
                    "✏️ 请直接输入你的回答：",
                    reply_markup=None,
                )
                return
            if not cartridge_id:
                await query.edit_message_text("请先选择一个卡带。")
                return
            result = await harness.process(user_id=user_id, message=answer, cartridge_id=cartridge_id)
            await self._reply(query.edit_message_text, result, cartridge_id, telegram_id)
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
            await self._reply(query.edit_message_text, result, cart_id, telegram_id)

        elif data == "/progress":
            result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
            kb = _learning_keyboard() if cartridge_id else _main_menu_keyboard()
            await query.edit_message_text(result.text, reply_markup=kb)

        elif data == "/back":
            result = await harness.process(user_id=user_id, message="/back", cartridge_id=cartridge_id)
            await self._reply(query.edit_message_text, result, cartridge_id, telegram_id)

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
        await self._reply(update.message.reply_text, result, cartridge_id, telegram_id)

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
        await self._reply(update.message.reply_text, result, cartridge_id, telegram_id)
