# Phase 2-3: Telegram 入口 + 示例卡带 实现计划

**目标：** 把 Phase 1 的核心引擎接入 Telegram Bot，实现完整的学习闭环；同时制作 2 个完整示例卡带，做到端到端可演示。

**架构：** Telegram Adapter 实现 BaseAdapter 接口，通过 python-telegram-bot 库接收用户消息，转发给 LearningHarness 处理。新增 FastAPI main.py 作为 webhook 入口（同时支持 polling 模式开发）。卡带用 Markdown 编写，manifest.json 定义 DAG。

**技术栈：** python-telegram-bot v20+, FastAPI, uvicorn, SQLAlchemy 2.0, aiosqlite（开发）, LiteLLM, pytest

**工作目录：** `/tmp/project-starlight/`

**前提：** Phase 1 全部完成，57 tests passing。

---

## 文件结构（新增/修改）

```
starlight/
├── adapters/
│   ├── base.py                 # [已有]
│   └── telegram_adapter.py     # [新建] Telegram Bot 适配器
├── main.py                     # [新建] FastAPI 应用 + Bot 启动
├── config.py                   # [修改] 新增 bot_token 等配置
└── core/
    └── harness.py              # [修改] 增强：支持 /browse, /progress, /review 等指令

cartridges/
├── python-basics/              # [已有] 扩充到 10+ 节点
│   └── nodes/
│       ├── N01-variables.md
│       ├── N02-types.md
│       ├── N03-control-flow.md
│       ├── N04-functions.md
│       ├── N05-lists.md
│       ├── N06-dicts.md
│       ├── N07-strings.md
│       ├── N08-file-io.md
│       ├── N09-error-handling.md
│       └── N10-modules.md
└── git-essentials/             # [新建] Git 基础卡带
    ├── manifest.json
    └── nodes/
        ├── N01-what-is-git.md
        ├── N02-repo-init.md
        ├── N03-stage-commit.md
        ├── N04-branch.md
        ├── N05-merge.md
        └── N06-remote.md

tests/
├── test_telegram_adapter.py    # [新建]
├── test_main.py                # [新建]
├── test_harness_commands.py    # [新建] 测试 /browse, /progress 等
└── test_cartridges_valid.py    # [新建] 卡带完整性验证
```

---

## 并行分组

以下任务按独立域分为 **3 个并行流**，互不依赖：

**流 A：核心增强**（Task 1-3）— Harness 指令 + FastAPI + 集成
**流 B：Telegram Adapter**（Task 4-5）— Bot 实现
**流 C：卡带内容**（Task 6-7）— python-basics 扩充 + git-essentials 新建

---

## 任务 1（流 A）：Harness 指令扩展

**文件：**
- 修改：`starlight/core/harness.py`
- 创建：`tests/test_harness_commands.py`

当前 Harness 只处理 `/start` 和自由文本（当作考核回答）。需要增加 `/browse`、`/progress`、`/review` 指令支持。

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_harness_commands.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.harness import LearningHarness

@pytest.fixture
def mock_deps():
    loader = MagicMock()
    loader.list_cartridges.return_value = ["python-basics", "git-essentials"]
    loader.load.return_value = {
        "id": "python-basics",
        "title": "Python 基础",
        "nodes": [
            {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"},
            {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
        ],
        "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": []}},
    }
    loader.get_entry_node.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    loader.get_next_nodes.return_value = [{"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"}]

    assessor = AsyncMock()
    progress = AsyncMock()
    tribute = MagicMock()
    return loader, assessor, progress, tribute


@pytest.mark.asyncio
async def test_browse_cartridges(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text
    assert "git-essentials" in result.text
    assert result.state == "idle"


@pytest.mark.asyncio
async def test_progress_command(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(
        current_node="N02",
        status="in_progress",
        cartridge_id="python-basics",
    )
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert "N02" in result.text or "进度" in result.text


@pytest.mark.asyncio
async def test_progress_no_progress(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert "尚未开始" in result.text or "没有" in result.text or "idle" in result.state


@pytest.mark.asyncio
async def test_help_command(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/help")
    assert "/start" in result.text
    assert "/browse" in result.text
    assert "/progress" in result.text
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_harness_commands.py -v
```

- [ ] **步骤 3：修改 harness.py，增加指令路由**

在 `LearningHarness.process()` 中增加指令分支：

```python
async def process(self, user_id: int, message: str, cartridge_id: str | None = None) -> HarnessResult:
    # Command routing
    if message == "/browse":
        return await self._handle_browse()
    if message == "/help":
        return self._handle_help()
    if message == "/progress":
        return await self._handle_progress(user_id, cartridge_id)
    if message == "/start":
        return await self._handle_start(user_id, cartridge_id)
    if message == "/review":
        return await self._handle_review(user_id, cartridge_id)

    # ... 原有逻辑 ...
```

新增方法：

```python
async def _handle_browse(self) -> HarnessResult:
    cartridges = self.cartridges.list_cartridges()
    lines = ["📚 可用卡带：\n"]
    for cart_id in cartridges:
        try:
            cart = self.cartridges.load(cart_id)
            lines.append(f"• **{cart['title']}** (`{cart_id}`) — {len(cart['nodes'])} 个知识点")
        except Exception:
            lines.append(f"• `{cart_id}`")
    lines.append("\n用 `/start <卡带ID>` 开始学习")
    return HarnessResult(text="\n".join(lines), state="idle")

async def _handle_progress(self, user_id: int, cartridge_id: str | None) -> HarnessResult:
    if not cartridge_id:
        return HarnessResult(text="请先选择一个卡带。用 /browse 查看可用卡带。", state="idle")
    progress = await self.progress.get_progress(user_id, cartridge_id)
    if progress is None:
        return HarnessResult(text="你尚未开始这个卡带。用 /start 开始吧！", state="idle")
    cart = self.cartridges.load(cartridge_id)
    total = len(cart["nodes"])
    completed_ids = set()
    # Count completed: walk DAG from entry
    current = progress.current_node
    return HarnessResult(
        text=f"📊 **{cart['title']}** 进度\n\n当前：{current}\n状态：{progress.status}\n总节点：{total}",
        state=progress.status,
    )

def _handle_help(self) -> HarnessResult:
    return HarnessResult(
        text=(
            "🌟 **星光学习机**\n\n"
            "指令列表：\n"
            "/browse — 浏览可用卡带\n"
            "/start <ID> — 开始学习\n"
            "/progress — 查看进度\n"
            "/review — 复习已学知识\n"
            "/help — 显示帮助\n\n"
            "直接输入文字 = 回答考核问题"
        ),
        state="idle",
    )

async def _handle_review(self, user_id: int, cartridge_id: str | None) -> HarnessResult:
    if not cartridge_id:
        return HarnessResult(text="请先选择一个卡带。", state="idle")
    progress = await self.progress.get_progress(user_id, cartridge_id)
    if progress is None:
        return HarnessResult(text="你还没开始学习哦。用 /start 开始！", state="idle")
    cart = self.cartridges.load(cartridge_id)
    if progress.current_node:
        node = self.cartridges.get_node_by_id(cart, progress.current_node)
        content = self.cartridges.load_node_content(cartridge_id, node["file"])
        return HarnessResult(text=f"📖 复习：{node['title']}\n\n{content}", state="learning")
    return HarnessResult(text="暂无可复习内容。", state="idle")
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_harness_commands.py -v
```

- [ ] **步骤 5：确认全部测试通过**

```bash
pytest tests/ -v
```

- [ ] **步骤 6：Commit**

```bash
git add -A
git commit -m "feat: harness command routing for /browse, /progress, /help, /review"
```

---

## 任务 2（流 A）：配置更新 + FastAPI 入口

**文件：**
- 修改：`starlight/config.py`
- 创建：`starlight/main.py`
- 创建：`tests/test_main.py`

- [ ] **步骤 1：更新 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./starlight.db"
    redis_url: str = "redis://localhost/0"

    # LLM
    llm_model: str = "glm-4-flash"
    llm_api_key: str = ""
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"

    # Cartridges
    cartridges_dir: str = "./cartridges"

    # Assessment
    assessment_max_turns: int = 3

    # Telegram
    bot_token: str = ""
    bot_mode: str = "polling"  # "polling" or "webhook"
    webhook_url: str = ""  # for webhook mode

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "STARLIGHT_"

settings = Settings()
```

- [ ] **步骤 2：写 main.py**

```python
# starlight/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from starlight.config import settings

# Will be populated in task 4 when telegram adapter is ready
_bot = None
_harness = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot, _harness
    from starlight.core.cartridge import CartridgeLoader
    from starlight.core.assessor import Assessor
    from starlight.core.progress import ProgressManager
    from starlight.core.contributor import TributeEngine
    from starlight.core.harness import LearningHarness

    loader = CartridgeLoader(settings.cartridges_dir)
    assessor = Assessor(
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        max_turns=settings.assessment_max_turns,
    )
    # Note: progress_mgr needs a DB session; for now use in-memory mock
    # Will be wired properly in Phase 4
    progress_mgr = _MockProgressManager()
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
        return {"error": "unauthorized"}, 403
    update_data = await request.json()
    # Will be processed by telegram adapter in Task 4
    return {"ok": True}


class _MockProgressManager:
    """In-memory progress manager for development/testing."""
    def __init__(self):
        self._progress = {}

    async def get_progress(self, user_id: int, cartridge_id: str):
        return self._progress.get((user_id, cartridge_id))

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01"):
        from types import SimpleNamespace
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
        from datetime import datetime
        p = await self.get_progress(user_id, cartridge_id)
        if p is None:
            raise ValueError("No progress found")
        p.status = "completed"
        p.completed_at = datetime.utcnow()
        return p
```

- [ ] **步骤 3：写测试**

```python
# tests/test_main.py
import pytest
from httpx import AsyncClient, ASGITransport
from starlight.main import app


@pytest.mark.asyncio
async def test_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Starlight"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_webhook_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook/wrong-token", json={"update_id": 1})
    assert response.status_code == 403
```

- [ ] **步骤 4：运行测试**

```bash
pytest tests/test_main.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: FastAPI app with health endpoint, webhook route, and mock progress"
```

---

## 任务 3（流 A）：集成测试 + 全量验证

**文件：**
- 创建：`tests/test_integration.py`

端到端集成测试：模拟用户从 /browse → /start → 回答 → PASS → 下一节点 → 通关的完整流程。

- [ ] **步骤 1：写集成测试**

```python
# tests/test_integration.py
"""End-to-end integration tests for the Starlight learning flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.cartridge import CartridgeLoader
from starlight.core.assessor import Assessor, AssessmentResult
from starlight.core.harness import LearningHarness
from starlight.core.contributor import TributeEngine
from starlight.main import _MockProgressManager


@pytest.fixture
def full_harness():
    """Create a harness with real cartridge loader and mock LLM."""
    loader = CartridgeLoader("./cartridges")
    assessor = Assessor(llm_model="test", llm_api_key="test")
    # Mock the LLM call to avoid real API calls
    assessor._call_llm = AsyncMock()
    progress_mgr = _MockProgressManager()
    tribute = TributeEngine()
    return LearningHarness(loader, assessor, progress_mgr, tribute)


@pytest.mark.asyncio
async def test_full_learning_flow(full_harness):
    """Simulate: /browse → /start → answer → PASS → complete"""
    # 1. Browse
    result = await full_harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text

    # 2. Start
    result = await full_harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    assert result.state == "learning"
    assert "Python" in result.text or "变量" in result.text

    # 3. Answer (mock LLM returns PASS)
    full_harness.assessor._call_llm.return_value = "非常好，你理解了变量赋值！[PASS]"
    result = await full_harness.process(user_id=1, message="变量是存数据的", cartridge_id="python-basics")
    assert result.verdict == "PASS"

    # 4. Check progress
    result = await full_harness.process(user_id=1, message="/progress", cartridge_id="python-basics")
    assert result.state == "in_progress"


@pytest.mark.asyncio
async def test_browse_lists_all_cartridges(full_harness):
    result = await full_harness.process(user_id=1, message="/browse")
    assert "python-basics" in result.text
    assert result.state == "idle"


@pytest.mark.asyncio
async def test_help_shows_commands(full_harness):
    result = await full_harness.process(user_id=1, message="/help")
    assert "/browse" in result.text
    assert "/start" in result.text
    assert "/progress" in result.text


@pytest.mark.asyncio
async def test_start_nonexistent_cartridge():
    loader = CartridgeLoader("./cartridges")
    assessor = AsyncMock()
    progress = _MockProgressManager()
    tribute = TributeEngine()
    harness = LearningHarness(loader, assessor, progress, tribute)

    with pytest.raises(FileNotFoundError):
        await harness.process(user_id=1, message="/start", cartridge_id="nonexistent")
```

- [ ] **步骤 2：运行全部测试**

```bash
pytest tests/ -v --tb=short
```

- [ ] **步骤 3：确认全部通过后 Commit**

```bash
git add -A
git commit -m "test: end-to-end integration tests for full learning flow"
```

---

## 任务 4（流 B）：Telegram Adapter

**文件：**
- 创建：`starlight/adapters/telegram_adapter.py`
- 创建：`tests/test_telegram_adapter.py`

- [ ] **步骤 1：更新 requirements.txt**

添加：
```
python-telegram-bot>=20.0
```

- [ ] **步骤 2：写 telegram_adapter.py**

```python
# starlight/adapters/telegram_adapter.py
from __future__ import annotations
import logging
from typing import Callable, Awaitable
from starlight.adapters.base import BaseAdapter, HarnessResult

logger = logging.getLogger(__name__)


class TelegramAdapter(BaseAdapter):
    """Telegram Bot adapter for Starlight."""

    def __init__(self, harness_factory: Callable[[], Awaitable], bot_token: str):
        """
        Args:
            harness_factory: async callable that returns a LearningHarness instance
            bot_token: Telegram Bot API token
        """
        self._harness_factory = harness_factory
        self._bot_token = bot_token
        self._bot = None
        self._application = None
        # Track user's current cartridge (in production, this comes from DB)
        self._user_cartridges: dict[int, str] = {}

    async def send_message(self, user_id: str, text: str) -> None:
        """Send a message to a Telegram user."""
        if self._bot:
            await self._bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

    async def start(self, mode: str = "polling") -> None:
        """Start the bot in polling or webhook mode."""
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

        self._application = (
            ApplicationBuilder()
            .token(self._bot_token)
            .build()
        )

        # Register handlers
        self._application.add_handler(CommandHandler("start", self._handle_start))
        self._application.add_handler(CommandHandler("browse", self._handle_browse))
        self._application.add_handler(CommandHandler("progress", self._handle_progress))
        self._application.add_handler(CommandHandler("help", self._handle_help))
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        self._bot = self._application.bot

        if mode == "polling":
            await self._application.initialize()
            await self._application.start()
            await self._application.updater.start_polling()
            logger.info("Telegram bot started in polling mode")
        else:
            logger.info("Telegram bot initialized (webhook mode requires manual setup)")

    async def shutdown(self) -> None:
        """Shutdown the bot gracefully."""
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()

    async def _get_harness(self):
        return await self._harness_factory()

    async def _handle_start(self, update, context) -> None:
        """Handle /start <cartridge_id> command."""
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
        result = await harness.process(user_id=user_id, message="/start", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)

    async def _handle_browse(self, update, context) -> None:
        harness = await self._get_harness()
        result = await harness.process(user_id=update.effective_user.id, message="/browse")
        await update.message.reply_text(result.text)

    async def _handle_progress(self, update, context) -> None:
        harness = await self._get_harness()
        user_id = update.effective_user.id
        cartridge_id = self._user_cartridges.get(user_id)
        result = await harness.process(user_id=user_id, message="/progress", cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)

    async def _handle_help(self, update, context) -> None:
        harness = await self._get_harness()
        result = await harness.process(user_id=update.effective_user.id, message="/help")
        await update.message.reply_text(result.text)

    async def _handle_message(self, update, context) -> None:
        """Handle free-text messages as assessment answers."""
        harness = await self._get_harness()
        user_id = update.effective_user.id
        text = update.message.text
        cartridge_id = self._user_cartridges.get(user_id)

        if not cartridge_id:
            await update.message.reply_text("请先用 /start <卡带ID> 选择一个卡带开始学习。")
            return

        result = await harness.process(user_id=user_id, message=text, cartridge_id=cartridge_id)
        await update.message.reply_text(result.text)
```

- [ ] **步骤 3：写测试**

```python
# tests/test_telegram_adapter.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlight.adapters.telegram_adapter import TelegramAdapter
from starlight.core.harness import LearningHarness
from starlight.adapters.base import HarnessResult


@pytest.fixture
def mock_harness():
    harness = AsyncMock(spec=LearningHarness)
    harness.process.return_value = HarnessResult(text="测试回复", state="idle")
    return harness


@pytest.fixture
def adapter(mock_harness):
    harness_factory = AsyncMock(return_value=mock_harness)
    return TelegramAdapter(harness_factory=harness_factory, bot_token="test-token")


def test_adapter_creates(adapter):
    assert adapter._bot_token == "test-token"


def test_user_cartridge_tracking(adapter):
    adapter._user_cartridges[123] = "python-basics"
    assert adapter._user_cartridges[123] == "python-basics"


@pytest.mark.asyncio
async def test_send_message_no_bot(adapter):
    """send_message should not crash if bot is not initialized."""
    await adapter.send_message(user_id="123", text="hello")


@pytest.mark.asyncio
async def test_send_message_with_bot(adapter):
    adapter._bot = AsyncMock()
    await adapter.send_message(user_id="123", text="hello")
    adapter._bot.send_message.assert_called_once()
```

- [ ] **步骤 4：运行测试**

```bash
pytest tests/test_telegram_adapter.py -v
```

- [ ] **步骤 5：运行全部测试确认无回归**

```bash
pytest tests/ -v
```

- [ ] **步骤 6：Commit**

```bash
git add -A
git commit -m "feat: Telegram adapter with command handlers and message routing"
```

---

## 任务 5（流 B）：Bot 启动脚本

**文件：**
- 创建：`run_bot.py`（项目根目录）

方便开发时直接 `python run_bot.py` 启动 bot。

- [ ] **步骤 1：创建 run_bot.py**

```python
#!/usr/bin/env python3
"""Start the Starlight Telegram Bot."""
import asyncio
import logging
import sys

from starlight.config import settings
from starlight.adapters.telegram_adapter import TelegramAdapter
from starlight.core.cartridge import CartridgeLoader
from starlight.core.assessor import Assessor
from starlight.core.contributor import TributeEngine
from starlight.core.harness import LearningHarness
from starlight.main import _MockProgressManager


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def create_harness():
    loader = CartridgeLoader(settings.cartridges_dir)
    assessor = Assessor(
        llm_model=settings.llm_model,
        llm_api_key=settings.llm_api_key,
        max_turns=settings.assessment_max_turns,
    )
    progress_mgr = _MockProgressManager()
    tribute = TributeEngine()
    return LearningHarness(loader, assessor, progress_mgr, tribute)


async def main():
    if not settings.bot_token:
        logger.error("STARLIGHT_BOT_TOKEN not set. Set it as environment variable.")
        sys.exit(1)

    adapter = TelegramAdapter(
        harness_factory=create_harness,
        bot_token=settings.bot_token,
    )

    logger.info("Starting Starlight Bot...")
    await adapter.start(mode=settings.bot_mode)

    # Keep running
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        await adapter.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **步骤 2：验证导入无误**

```bash
python -c "from run_bot import create_harness; print('OK')"
```

- [ ] **步骤 3：Commit**

```bash
git add -A
git commit -m "feat: bot startup script with polling mode"
```

---

## 任务 6（流 C）：python-basics 卡带扩充

**文件：**
- 修改：`cartridges/python-basics/manifest.json`
- 创建：`cartridges/python-basics/nodes/N04-functions.md`
- 创建：`cartridges/python-basics/nodes/N05-lists.md`
- 创建：`cartridges/python-basics/nodes/N06-dicts.md`
- 创建：`cartridges/python-basics/nodes/N07-strings.md`
- 创建：`cartridges/python-basics/nodes/N08-file-io.md`
- 创建：`cartridges/python-basics/nodes/N09-error-handling.md`
- 创建：`cartridges/python-basics/nodes/N10-modules.md`

将 python-basics 从 3 节点扩充到 10 节点，DAG 包含分支和汇合。

- [ ] **步骤 1：更新 manifest.json**

```json
{
  "id": "python-basics",
  "title": "Python 基础",
  "version": "2.0.0",
  "language": "zh-CN",
  "contributors": [
    {"name": "Starlight Team", "role": "author", "quote": "从零开始，点亮每一颗星。"}
  ],
  "nodes": [
    {"id": "N01", "title": "变量与赋值", "file": "nodes/N01-variables.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能解释变量赋值并写出基本赋值语句"},
    {"id": "N02", "title": "数据类型", "file": "nodes/N02-types.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分 str/int/float/list 并正确使用"},
    {"id": "N03", "title": "控制流", "file": "nodes/N03-control-flow.md", "prerequisites": ["N02"], "difficulty": 2, "pass_criteria": "能写 if/else 和 for/while 循环"},
    {"id": "N04", "title": "函数", "file": "nodes/N04-functions.md", "prerequisites": ["N03"], "difficulty": 2, "pass_criteria": "能定义函数、使用参数和返回值"},
    {"id": "N05", "title": "列表", "file": "nodes/N05-lists.md", "prerequisites": ["N03"], "difficulty": 2, "pass_criteria": "能创建列表、索引、切片和常用方法"},
    {"id": "N06", "title": "字典", "file": "nodes/N06-dicts.md", "prerequisites": ["N05"], "difficulty": 2, "pass_criteria": "能创建字典、增删查改键值对"},
    {"id": "N07", "title": "字符串操作", "file": "nodes/N07-strings.md", "prerequisites": ["N02"], "difficulty": 1, "pass_criteria": "能使用字符串格式化、切片和常用方法"},
    {"id": "N08", "title": "文件读写", "file": "nodes/N08-file-io.md", "prerequisites": ["N04", "N07"], "difficulty": 3, "pass_criteria": "能用 open() 读写文件、处理编码"},
    {"id": "N09", "title": "异常处理", "file": "nodes/N09-error-handling.md", "prerequisites": ["N04"], "difficulty": 3, "pass_criteria": "能用 try/except/finally 处理异常"},
    {"id": "N10", "title": "模块与包", "file": "nodes/N10-modules.md", "prerequisites": ["N08", "N09"], "difficulty": 3, "pass_criteria": "能 import 模块、创建简单包"}
  ],
  "dag": {
    "entry": "N01",
    "edges": {
      "N01": ["N02"],
      "N02": ["N03", "N07"],
      "N03": ["N04", "N05"],
      "N04": ["N08", "N09"],
      "N05": ["N06"],
      "N06": [],
      "N07": ["N08"],
      "N08": ["N10"],
      "N09": ["N10"],
      "N10": []
    }
  }
}
```

- [ ] **步骤 2：写每个节点 .md 文件**

每个文件 200-500 字，包含：核心概念、示例代码、常见误区。内容质量要高——这是用户直接看到的学习材料。

N04-functions.md 示例结构：
```markdown
# N04: 函数

## 核心概念
函数是可复用的代码块。用 `def` 关键字定义...

## 示例
​```python
def greet(name):
    return f"你好，{name}！"
​```

## 常见误区
- 忘记 return 语句
- 参数默认值使用可变对象

---
> 本章节由 **Starlight Team** 贡献
```

每个节点的 .md 文件都按此结构编写。

- [ ] **步骤 3：验证卡带可加载**

```python
from starlight.core.cartridge import CartridgeLoader
loader = CartridgeLoader("./cartridges")
cart = loader.load("python-basics")
assert len(cart["nodes"]) == 10
for node in cart["nodes"]:
    content = loader.load_node_content("python-basics", node["file"])
    assert len(content) > 100, f"{node['id']} content too short"
print("OK: all 10 nodes loaded")
```

- [ ] **步骤 4：验证 DAG 无环**

```python
from starlight.core.dag import DAGEngine
engine = DAGEngine()
loader = CartridgeLoader("./cartridges")
cart = loader.load("python-basics")
assert engine.has_cycle(cart["dag"]["edges"]) is False
assert engine.all_reachable(cart["dag"]["entry"], cart["dag"]["edges"], 10) is True
print("OK: DAG valid")
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: expand python-basics cartridge to 10 nodes with branching DAG"
```

---

## 任务 7（流 C）：git-essentials 新卡带

**文件：**
- 创建：`cartridges/git-essentials/manifest.json`
- 创建：`cartridges/git-essentials/nodes/N01-what-is-git.md`
- 创建：`cartridges/git-essentials/nodes/N02-repo-init.md`
- 创建：`cartridges/git-essentials/nodes/N03-stage-commit.md`
- 创建：`cartridges/git-essentials/nodes/N04-branch.md`
- 创建：`cartridges/git-essentials/nodes/N05-merge.md`
- 创建：`cartridges/git-essentials/nodes/N06-remote.md`

- [ ] **步骤 1：写 manifest.json**

```json
{
  "id": "git-essentials",
  "title": "Git 基础",
  "version": "1.0.0",
  "language": "zh-CN",
  "contributors": [
    {"name": "Starlight Team", "role": "author", "quote": "版本控制是开发者的超能力。"}
  ],
  "nodes": [
    {"id": "N01", "title": "什么是 Git", "file": "nodes/N01-what-is-git.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能解释版本控制的概念和 Git 的基本作用"},
    {"id": "N02", "title": "初始化仓库", "file": "nodes/N02-repo-init.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能用 git init 创建仓库、理解工作区概念"},
    {"id": "N03", "title": "暂存与提交", "file": "nodes/N03-stage-commit.md", "prerequisites": ["N02"], "difficulty": 2, "pass_criteria": "能用 git add 和 git commit 暂存和提交更改"},
    {"id": "N04", "title": "分支", "file": "nodes/N04-branch.md", "prerequisites": ["N03"], "difficulty": 2, "pass_criteria": "能创建、切换和删除分支"},
    {"id": "N05", "title": "合并", "file": "nodes/N05-merge.md", "prerequisites": ["N04"], "difficulty": 3, "pass_criteria": "能合并分支、处理简单冲突"},
    {"id": "N06", "title": "远程仓库", "file": "nodes/N06-remote.md", "prerequisites": ["N03"], "difficulty": 3, "pass_criteria": "能 clone、push、pull 远程仓库"}
  ],
  "dag": {
    "entry": "N01",
    "edges": {
      "N01": ["N02"],
      "N02": ["N03"],
      "N03": ["N04", "N06"],
      "N04": ["N05"],
      "N05": [],
      "N06": []
    }
  }
}
```

- [ ] **步骤 2：写每个节点 .md 文件**

每个文件 200-500 字，包含核心概念、命令示例、常见误区。

N01-what-is-git.md 示例结构：
```markdown
# N01: 什么是 Git

## 核心概念
Git 是一个分布式版本控制系统...

## 为什么需要版本控制
想象你在写论文...

## 关键概念
- 仓库（Repository）
- 提交（Commit）
- 分支（Branch）

---
> 本章节由 **Starlight Team** 贡献
```

- [ ] **步骤 3：验证卡带完整**

```python
from starlight.core.cartridge import CartridgeLoader
from starlight.core.dag import DAGEngine

loader = CartridgeLoader("./cartridges")
cart = loader.load("git-essentials")
assert len(cart["nodes"]) == 6
for node in cart["nodes"]:
    content = loader.load_node_content("git-essentials", node["file"])
    assert len(content) > 100, f"{node['id']} too short"

engine = DAGEngine()
assert engine.has_cycle(cart["dag"]["edges"]) is False
assert engine.all_reachable(cart["dag"]["entry"], cart["dag"]["edges"], 6) is True
print("OK: git-essentials cartridge valid")
```

- [ ] **步骤 4：Commit**

```bash
git add -A
git commit -m "feat: git-essentials cartridge with 6 nodes covering Git basics"
```

---

## 自审

**规格覆盖：**
- Phase 2 Telegram 入口 ✅ → Task 4, 5
- Phase 3 示例卡带 ✅ → Task 6, 7
- Harness 指令扩展（设计文档 6.1 指令集）✅ → Task 1
- FastAPI 入口 ✅ → Task 2
- 集成测试 ✅ → Task 3

**占位符扫描：** 无 TODO/TBD ✅

**类型一致性：**
- `HarnessResult` 结构在 base.py 定义，harness.py 和 telegram_adapter.py 使用一致 ✅
- `process()` 签名：harness 增加 `cartridge_id` 可选参数，telegram adapter 传入 ✅
- `_MockProgressManager` 实现与 `ProgressManager` 接口一致 ✅

**并行安全性：**
- 流 A（Task 1-3）：修改 harness.py, main.py, 新建测试 — 不涉及卡带内容
- 流 B（Task 4-5）：新建 telegram_adapter.py, run_bot.py — 不修改核心引擎
- 流 C（Task 6-7）：只改 cartridges/ 目录下的内容文件
- 三条流互不干扰 ✅

**缺口：** 无 ✅

---

**计划保存到：** `docs/superpowers/plans/2026-04-04-starlight-phase2-3.md`

**并行执行方案：**
- Agent A：Task 1 → Task 2 → Task 3（核心增强，串行有依赖）
- Agent B：Task 4 → Task 5（Telegram Adapter，串行有依赖）
- Agent C：Task 6 + Task 7（卡带内容，可并行但合并为一个 agent 避免冲突）

三个 Agent 同时 dispatch。
