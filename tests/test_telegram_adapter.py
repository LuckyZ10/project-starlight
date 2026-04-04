"""Tests for starlight.adapters.telegram_adapter."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlight.adapters.telegram_adapter import TelegramAdapter
from starlight.adapters.base import HarnessResult
from starlight.core.harness_v2 import LearningHarnessV2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_harness():
    harness = AsyncMock(spec=LearningHarnessV2)
    harness.process.return_value = HarnessResult(text="测试回复", state="idle")
    return harness


@pytest.fixture
def adapter(mock_harness):
    factory = AsyncMock(return_value=mock_harness)
    return TelegramAdapter(harness_factory=factory, bot_token="test-token-123")


# ---------------------------------------------------------------------------
# Construction & basic state
# ---------------------------------------------------------------------------


def test_adapter_creates(adapter):
    assert adapter._bot_token == "test-token-123"
    assert adapter._harness is None


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_no_bot(adapter):
    """Should not crash when bot is not initialised."""
    await adapter.send_message(user_id="123", text="hello")


@pytest.mark.asyncio
async def test_send_message_with_bot(adapter):
    adapter._bot = AsyncMock()
    await adapter.send_message(user_id="123", text="hello world")
    adapter._bot.send_message.assert_called_once_with(
        chat_id="123", text="hello world", parse_mode="Markdown"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_update(user_id=42, text="", args=None, full_name="TestUser"):
    """Build a lightweight fake ``Update`` object."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.full_name = full_name
    update.message.text = text
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = args or []
    return update, context


# ---------------------------------------------------------------------------
# Command handler delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_start_with_cartridge(adapter, mock_harness):
    update, context = _make_update(args=["python-basics"])
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value=None):
        await adapter._handle_start(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/start", cartridge_id="python-basics"
    )
    update.message.reply_text.assert_called_once_with("测试回复")


@pytest.mark.asyncio
async def test_handle_start_without_cartridge_no_active(adapter, mock_harness):
    update, context = _make_update(args=[])
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value=None):
        await adapter._handle_start(update, context)

    mock_harness.process.assert_not_called()
    reply = update.message.reply_text.call_args[0][0]
    assert "/browse" in reply


@pytest.mark.asyncio
async def test_handle_start_without_cartridge_has_active(adapter, mock_harness):
    update, context = _make_update(args=[])
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value="python-basics"):
        await adapter._handle_start(update, context)

    mock_harness.process.assert_not_called()
    reply = update.message.reply_text.call_args[0][0]
    assert "python-basics" in reply


@pytest.mark.asyncio
async def test_handle_browse(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1):
        await adapter._handle_browse(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/browse"
    )


@pytest.mark.asyncio
async def test_handle_help(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1):
        await adapter._handle_help(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/help"
    )


@pytest.mark.asyncio
async def test_handle_progress_with_cartridge(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value="python-basics"):
        await adapter._handle_progress(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/progress", cartridge_id="python-basics"
    )


@pytest.mark.asyncio
async def test_handle_progress_without_cartridge(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value=None):
        await adapter._handle_progress(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/progress", cartridge_id=None
    )


@pytest.mark.asyncio
async def test_handle_message_with_cartridge(adapter, mock_harness):
    update, context = _make_update(text="变量是存数据的")
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value="python-basics"):
        await adapter._handle_message(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="变量是存数据的", cartridge_id="python-basics"
    )


@pytest.mark.asyncio
async def test_handle_message_without_cartridge(adapter, mock_harness):
    update, context = _make_update(text="随便说说")
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value=None):
        await adapter._handle_message(update, context)

    mock_harness.process.assert_not_called()
    reply = update.message.reply_text.call_args[0][0]
    assert "/start" in reply


# ---------------------------------------------------------------------------
# V2 Commands: /stats, /review
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_stats(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1):
        await adapter._handle_stats(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/stats"
    )
    update.message.reply_text.assert_called_once_with("测试回复")


@pytest.mark.asyncio
async def test_handle_review(adapter, mock_harness):
    update, context = _make_update()
    with patch("starlight.adapters.telegram_adapter.ensure_user", new_callable=AsyncMock, return_value=1), \
         patch("starlight.adapters.telegram_adapter.get_active_cartridge", new_callable=AsyncMock, return_value=None):
        await adapter._handle_review(update, context)

    mock_harness.process.assert_called_once_with(
        user_id=1, message="/review", cartridge_id=None
    )
    update.message.reply_text.assert_called_once_with("测试回复")
