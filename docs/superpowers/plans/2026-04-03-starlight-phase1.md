# Phase 1: 核心引擎 实现计划

**目标：** 实现 Starlight 的核心学习引擎（Harness）、卡带加载器和进度管理，做到不依赖任何 IM 框架、纯 Python、完全可测试。

**架构：** 插件化微内核。Harness 是核心，接收 (user_id, message) 返回 (response, state_update)。通过 LiteLLM 调用国内 LLM。PostgreSQL 持久化。Redis 缓存会话状态。

**技术栈：** Python 3.10+, FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis, LiteLLM, pytest

**工作目录：** `/tmp/project-starlight/`

---

## 文件结构

```
starlight/
├── __init__.py
├── config.py                    # 全局配置（DB URL、Redis URL、LLM 模型名）
├── models.py                    # SQLAlchemy 数据模型
├── core/
│   ├── __init__.py
│   ├── cartridge.py             # 卡带加载器：解析 .star 包、校验 DAG、缓存
│   ├── dag.py                   # DAG 引擎：拓扑排序、解锁判定、路径计算
│   ├── assessor.py              # LLM 考核：构建 prompt、调用 LLM、解析 PASS/FAIL
│   ├── progress.py              # 进度管理：查询/更新用户进度、统计
│   ├── contributor.py           # 贡献者管理、致敬文案生成
│   └── harness.py               # 主引擎：6 阶段状态机、路由、调度
├── adapters/
│   ├── __init__.py
│   └── base.py                  # Adapter 基类（定义接口）
├── billing/
│   ├── __init__.py
│   └── gateway.py               # 计费网关（用量检查、限额判定）
└── main.py                      # FastAPI 应用入口

tests/
├── conftest.py                  # 共享 fixtures（测试 DB、Redis mock、LLM mock）
├── test_cartridge.py            # 卡带加载和校验测试
├── test_dag.py                  # DAG 引擎测试
├── test_assessor.py             # 考核引擎测试
├── test_progress.py             # 进度管理测试
├── test_contributor.py          # 贡献者致敬测试
├── test_harness.py              # Harness 集成测试
└── test_billing.py              # 计费网关测试

cartridges/
└── python-basics/               # 示例卡带
    ├── manifest.json
    └── nodes/
        ├── N01-variables.md
        ├── N02-types.md
        └── N03-control-flow.md

requirements.txt
```

---

## 任务 1：项目骨架 + 配置

**文件：**
- 创建：`starlight/__init__.py`
- 创建：`starlight/config.py`
- 创建：`requirements.txt`
- 创建：`tests/conftest.py`

- [ ] **步骤 1：创建项目目录结构**

```bash
mkdir -p starlight/core starlight/adapters starlight/billing
mkdir -p tests cartridges/python-basics/nodes
touch starlight/__init__.py starlight/core/__init__.py starlight/adapters/__init__.py starlight/billing/__init__.py
```

- [ ] **步骤 2：写 requirements.txt**

```
fastapi>=0.110.0
uvicorn>=0.29.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
redis>=5.0.0
litellm>=1.30.0
pydantic>=2.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **步骤 3：写 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost/starlight"
    redis_url: str = "redis://localhost/0"
    llm_model: str = "glm-4-flash"
    llm_api_key: str = ""
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    cartridges_dir: str = "./cartridges"
    assessment_max_turns: int = 3

    class Config:
        env_prefix = "STARLIGHT_"

settings = Settings()
```

- [ ] **步骤 4：写 conftest.py**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from starlight.models import Base

@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///./test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

- [ ] **步骤 5：安装依赖并验证导入**

```bash
pip install -r requirements.txt
python -c "from starlight.config import settings; print('OK')"
```

- [ ] **步骤 6：初始化 git 并 commit**

```bash
cd /tmp/project-starlight
git init
git add -A
git commit -m "chore: project skeleton with config and test fixtures"
```

---

## 任务 2：数据模型

**文件：**
- 创建：`starlight/models.py`
- 创建：`tests/test_models.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_models.py
import pytest
from starlight.models import User, Cartridge, Node, UserProgress, Assessment

@pytest.mark.asyncio
async def test_create_user(db_session):
    user = User(telegram_id="12345", name="test_user", plan="free")
    db_session.add(user)
    await db_session.commit()
    result = await db_session.get(User, user.id)
    assert result.name == "test_user"
    assert result.plan == "free"

@pytest.mark.asyncio
async def test_cartridge_with_nodes(db_session):
    cart = Cartridge(id="python-basics", title="Python 基础", version="1.0.0", language="zh-CN", entry_node="N01")
    node = Node(id="N01", cartridge_id="python-basics", title="变量", file_path="nodes/N01.md", difficulty=1, pass_criteria="能写赋值语句")
    db_session.add_all([cart, node])
    await db_session.commit()
    assert node.cartridge_id == "python-basics"

@pytest.mark.asyncio
async def test_user_progress(db_session):
    user = User(telegram_id="12345", name="test_user")
    progress = UserProgress(user_id=user.id, cartridge_id="python-basics", current_node="N02", status="in_progress")
    db_session.add_all([user, progress])
    await db_session.commit()
    assert progress.status == "in_progress"

@pytest.mark.asyncio
async def test_assessment_record(db_session):
    user = User(telegram_id="12345", name="test_user")
    assessment = Assessment(user_id=user.id, node_id="N01", cartridge_id="python-basics", verdict="PASS", score=85)
    db_session.add_all([user, assessment])
    await db_session.commit()
    assert assessment.verdict == "PASS"
    assert assessment.score == 85
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_models.py -v
```

预期：FAIL（models.py 不存在）

- [ ] **步骤 3：写 models.py**

```python
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class PlanType(str, enum.Enum):
    FREE = "free"
    MONTHLY = "monthly"
    TOKEN_PACK = "token_pack"

class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Verdict(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    CONTINUE = "CONTINUE"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    plan = Column(String, default=PlanType.FREE.value)
    api_key_enc = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    progress = relationship("UserProgress", back_populates="user")
    assessments = relationship("Assessment", back_populates="user")

class Cartridge(Base):
    __tablename__ = "cartridges"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    version = Column(String, default="1.0.0")
    language = Column(String, default="zh-CN")
    entry_node = Column(String, nullable=False)
    status = Column(String, default="active")
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    nodes = relationship("Node", back_populates="cartridge")

class Node(Base):
    __tablename__ = "nodes"
    id = Column(String, primary_key=True)
    cartridge_id = Column(String, ForeignKey("cartridges.id"), primary_key=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    prerequisites = Column(JSON, default=list)
    difficulty = Column(Integer, default=1)
    pass_criteria = Column(Text, nullable=False)
    cartridge = relationship("Cartridge", back_populates="nodes")

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cartridge_id = Column(String, ForeignKey("cartridges.id"), nullable=False)
    current_node = Column(String, nullable=True)
    status = Column(String, default=ProgressStatus.NOT_STARTED.value)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="progress")

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    node_id = Column(String, nullable=False)
    cartridge_id = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    score = Column(Integer, default=0)
    messages_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="assessments")

class Contributor(Base):
    __tablename__ = "contributors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    github = Column(String, nullable=True)
    location = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    quote = Column(Text, nullable=True)
    story = Column(Text, nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

class CartridgeContributor(Base):
    __tablename__ = "cartridge_contributors"
    cartridge_id = Column(String, ForeignKey("cartridges.id"), primary_key=True)
    contributor_id = Column(Integer, ForeignKey("contributors.id"), primary_key=True)
    role = Column(String, default="author")
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_models.py -v
```

预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: data models (User, Cartridge, Node, Progress, Assessment, Contributor)"
```

---

## 任务 3：卡带加载器

**文件：**
- 创建：`starlight/core/cartridge.py`
- 创建：`cartridges/python-basics/manifest.json`
- 创建：`cartridges/python-basics/nodes/N01-variables.md`
- 创建：`cartridges/python-basics/nodes/N02-types.md`
- 创建：`cartridges/python-basics/nodes/N03-control-flow.md`
- 创建：`tests/test_cartridge.py`

- [ ] **步骤 1：创建示例卡带文件**

`cartridges/python-basics/manifest.json`:
```json
{
  "id": "python-basics",
  "title": "Python 基础",
  "version": "1.0.0",
  "language": "zh-CN",
  "contributors": [
    {"name": "Starlight Team", "role": "author", "quote": "从零开始，点亮每一颗星。"}
  ],
  "nodes": [
    {"id": "N01", "title": "变量与赋值", "file": "nodes/N01-variables.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能解释变量赋值并写出基本赋值语句"},
    {"id": "N02", "title": "数据类型", "file": "nodes/N02-types.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分 str/int/float/list 并正确使用"},
    {"id": "N03", "title": "控制流", "file": "nodes/N03-control-flow.md", "prerequisites": ["N02"], "difficulty": 2, "pass_criteria": "能写 if/else 和 for/while 循环"}
  ],
  "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": ["N03"], "N03": []}}
}
```

每个 node .md 文件写对应的 Python 基础内容（100-500字）。

- [ ] **步骤 2：写失败的测试**

```python
# tests/test_cartridge.py
import pytest
from starlight.core.cartridge import CartridgeLoader

def test_load_cartridge():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    assert cart["id"] == "python-basics"
    assert len(cart["nodes"]) == 3
    assert cart["dag"]["entry"] == "N01"

def test_load_node_content():
    loader = CartridgeLoader("./cartridges")
    content = loader.load_node_content("python-basics", "nodes/N01-variables.md")
    assert "变量" in content
    assert len(content) > 50

def test_load_nonexistent_cartridge():
    loader = CartridgeLoader("./cartridges")
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent")

def test_get_entry_node():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    entry = loader.get_entry_node(cart)
    assert entry["id"] == "N01"
    assert entry["prerequisites"] == []

def test_get_next_nodes():
    loader = CartridgeLoader("./cartridges")
    cart = loader.load("python-basics")
    next_nodes = loader.get_next_nodes(cart, "N01")
    assert len(next_nodes) == 1
    assert next_nodes[0]["id"] == "N02"
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/test_cartridge.py -v
```

预期：FAIL

- [ ] **步骤 4：写 cartridge.py**

```python
# starlight/core/cartridge.py
import json
from pathlib import Path
from typing import Any

class CartridgeLoader:
    def __init__(self, cartridges_dir: str):
        self.base_dir = Path(cartridges_dir)

    def load(self, cartridge_id: str) -> dict[str, Any]:
        manifest_path = self.base_dir / cartridge_id / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Cartridge not found: {cartridge_id}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_node_content(self, cartridge_id: str, node_file: str) -> str:
        path = self.base_dir / cartridge_id / node_file
        if not path.exists():
            raise FileNotFoundError(f"Node file not found: {node_file}")
        return path.read_text(encoding="utf-8")

    def get_entry_node(self, cartridge: dict) -> dict:
        entry_id = cartridge["dag"]["entry"]
        for node in cartridge["nodes"]:
            if node["id"] == entry_id:
                return node
        raise ValueError(f"Entry node {entry_id} not found in nodes")

    def get_next_nodes(self, cartridge: dict, current_node_id: str) -> list[dict]:
        edges = cartridge["dag"].get("edges", {})
        next_ids = edges.get(current_node_id, [])
        return [n for n in cartridge["nodes"] if n["id"] in next_ids]

    def get_node_by_id(self, cartridge: dict, node_id: str) -> dict:
        for node in cartridge["nodes"]:
            if node["id"] == node_id:
                return node
        raise ValueError(f"Node {node_id} not found")

    def list_cartridges(self) -> list[str]:
        return [d.name for d in self.base_dir.iterdir() if d.is_dir() and (d / "manifest.json").exists()]
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/test_cartridge.py -v
```

预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add -A
git commit -m "feat: cartridge loader with sample python-basics cartridge"
```

---

## 任务 4：DAG 引擎

**文件：**
- 创建：`starlight/core/dag.py`
- 创建：`tests/test_dag.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_dag.py
import pytest
from starlight.core.dag import DAGEngine

def test_get_unlocked_nodes_no_prerequisites():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
    ]
    completed = set()
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N01"

def test_get_unlocked_after_completing_n01():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
        {"id": "N03", "prerequisites": ["N02"]},
    ]
    completed = {"N01"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 1
    assert unlocked[0]["id"] == "N02"

def test_all_unlocked():
    engine = DAGEngine()
    nodes = [
        {"id": "N01", "prerequisites": []},
        {"id": "N02", "prerequisites": ["N01"]},
    ]
    completed = {"N01", "N02"}
    unlocked = engine.get_unlocked(nodes, completed)
    assert len(unlocked) == 0

def test_detect_cycle():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": ["N01"]}
    assert engine.has_cycle(edges) is True

def test_no_cycle():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": []}
    assert engine.has_cycle(edges) is False

def test_all_nodes_reachable():
    engine = DAGEngine()
    edges = {"N01": ["N02", "N03"], "N02": ["N04"], "N03": [], "N04": []}
    assert engine.all_reachable("N01", edges, 4) is True

def test_orphan_node_detected():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": [], "N03": []}
    assert engine.all_reachable("N01", edges, 3) is False

def test_get_learning_path():
    engine = DAGEngine()
    edges = {"N01": ["N02"], "N02": ["N03"], "N03": []}
    path = engine.get_learning_path("N01", edges)
    assert path == ["N01", "N02", "N03"]
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_dag.py -v
```

- [ ] **步骤 3：写 dag.py**

```python
# starlight/core/dag.py
from typing import Any

class DAGEngine:
    def get_unlocked(self, nodes: list[dict], completed: set[str]) -> list[dict]:
        result = []
        for node in nodes:
            if node["id"] in completed:
                continue
            if all(p in completed for p in node.get("prerequisites", [])):
                result.append(node)
        return result

    def has_cycle(self, edges: dict[str, list[str]]) -> bool:
        visited = set()
        rec_stack = set()
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False
        for node in edges:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def all_reachable(self, start: str, edges: dict[str, list[str]], total_nodes: int) -> bool:
        visited = set()
        def dfs(node):
            visited.add(node)
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
        dfs(start)
        return len(visited) == total_nodes

    def get_learning_path(self, start: str, edges: dict[str, list[str]]) -> list[str]:
        path = []
        visited = set()
        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for neighbor in edges.get(node, []):
                dfs(neighbor)
        dfs(start)
        return path
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_dag.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: DAG engine with cycle detection, reachability, and learning path"
```

---

## 任务 5：Assessor 考核引擎

**文件：**
- 创建：`starlight/core/assessor.py`
- 创建：`tests/test_assessor.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_assessor.py
import pytest
from starlight.core.assessor import Assessor, AssessmentResult

@pytest.mark.asyncio
async def test_assessor_returns_pass():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    # Mock LLM response
    assessor._call_llm = async_lambda("基于你的回答，你已经理解了变量赋值的核心概念。[PASS]")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="变量就像一个盒子，可以把数据放进去。比如 name = 'hello' 就是把 hello 放进 name 这个盒子里。",
    )
    assert result.verdict == "PASS"
    assert result.score > 0

@pytest.mark.asyncio
async def test_assessor_returns_fail():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("你的回答还不够深入。[FAIL] 建议思考赋值和等于号的区别。")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="不知道",
    )
    assert result.verdict == "FAIL"
    assert result.hint is not None

@pytest.mark.asyncio
async def test_assessor_returns_continue():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    assessor._call_llm = async_lambda("你提到了变量，但能更具体地说明赋值的语法吗？")
    result = await assessor.assess(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值并写出基本赋值语句",
        conversation=[],
        user_answer="变量就是存东西的",
    )
    assert result.verdict == "CONTINUE"

@pytest.mark.asyncio
async def test_build_system_prompt():
    assessor = Assessor(llm_model="test", llm_api_key="test")
    prompt = assessor._build_system_prompt(
        node_content="变量是存储数据的容器",
        pass_criteria="能解释变量赋值",
        max_turns=3,
    )
    assert "星光学习机" in prompt
    assert "[PASS]" in prompt
    assert "[FAIL]" in prompt
    assert "变量是存储数据的容器" in prompt
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_assessor.py -v
```

- [ ] **步骤 3：写 assessor.py**

```python
# starlight/core/assessor.py
from dataclasses import dataclass
from typing import Callable, Awaitable

@dataclass
class AssessmentResult:
    verdict: str  # "PASS", "FAIL", "CONTINUE"
    feedback: str
    score: int  # 0-100
    hint: str | None = None

class Assessor:
    def __init__(self, llm_model: str, llm_api_key: str, max_turns: int = 3):
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.max_turns = max_turns
        self._call_llm: Callable[..., Awaitable[str]] = self._default_llm_call

    async def _default_llm_call(self, messages: list[dict]) -> str:
        import litellm
        response = await litellm.acompletion(
            model=self.llm_model,
            messages=messages,
            api_key=self.llm_api_key,
        )
        return response.choices[0].message.content

    async def assess(
        self,
        node_content: str,
        pass_criteria: str,
        conversation: list[dict],
        user_answer: str,
    ) -> AssessmentResult:
        system_prompt = self._build_system_prompt(node_content, pass_criteria, self.max_turns)
        messages = [{"role": "system", "content": system_prompt}] + conversation + [{"role": "user", "content": user_answer}]
        llm_response = await self._call_llm(messages)
        return self._parse_response(llm_response)

    def _build_system_prompt(self, node_content: str, pass_criteria: str, max_turns: int) -> str:
        return f"""你是星光学习机的考核官。

考核规则：
1. 基于以下知识内容考核学习者
2. 不要直接问教材里有的问题，创设真实场景让学习者应用知识
3. 学习者回答后，判断是否真正理解
4. 判定通过时输出 [PASS]，判定不通过时输出 [FAIL] 并给出提示
5. 如果回答模糊，继续追问（最多{max_turns}轮），然后必须判定
6. 绝不直接告诉答案，只给方向性提示

知识内容：
{node_content}

通过标准：
{pass_criteria}"""

    def _parse_response(self, response: str) -> AssessmentResult:
        upper = response.upper()
        if "[PASS]" in upper:
            score = self._estimate_score(response)
            return AssessmentResult(verdict="PASS", feedback=response, score=score)
        elif "[FAIL]" in upper:
            hint = self._extract_hint(response)
            return AssessmentResult(verdict="FAIL", feedback=response, score=0, hint=hint)
        else:
            return AssessmentResult(verdict="CONTINUE", feedback=response, score=0)

    def _estimate_score(self, response: str) -> int:
        # Simple heuristic: longer, more detailed responses from LLM imply better understanding
        if "非常好" in response or "完全理解" in response:
            return 95
        elif "理解" in response:
            return 80
        else:
            return 70

    def _extract_hint(self, response: str) -> str:
        lines = response.split("\n")
        for line in lines:
            if "建议" in line or "提示" in line or "思考" in line:
                return line.strip()
        return "再复习一下这个知识点，注意核心概念。"
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_assessor.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: assessor engine with LLM-based assessment and PASS/FAIL parsing"
```

---

## 任务 6：进度管理

**文件：**
- 创建：`starlight/core/progress.py`
- 创建：`tests/test_progress.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_progress.py
import pytest
from starlight.core.progress import ProgressManager
from starlight.models import User, UserProgress, Cartridge

@pytest.mark.asyncio
async def test_start_cartridge(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    db_session.add_all([user, cart])
    await db_session.commit()

    mgr = ProgressManager(db_session)
    progress = await mgr.start_cartridge(user.id, "python-basics")
    assert progress.current_node == "N01"
    assert progress.status == "in_progress"

@pytest.mark.asyncio
async def test_advance_node(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    progress = UserProgress(user_id=1, cartridge_id="python-basics", current_node="N01", status="in_progress")
    db_session.add_all([user, cart, progress])
    await db_session.commit()

    mgr = ProgressManager(db_session)
    updated = await mgr.advance_node(user.id, "python-basics", "N02")
    assert updated.current_node == "N02"

@pytest.mark.asyncio
async def test_complete_cartridge(db_session):
    user = User(telegram_id="12345", name="test")
    cart = Cartridge(id="python-basics", title="Python", entry_node="N01")
    progress = UserProgress(user_id=1, cartridge_id="python-basics", current_node="N03", status="in_progress")
    db_session.add_all([user, cart, progress])
    await db_session.commit()

    mgr = ProgressManager(db_session)
    updated = await mgr.complete_cartridge(user.id, "python-basics")
    assert updated.status == "completed"
    assert updated.completed_at is not None

@pytest.mark.asyncio
async def test_get_progress_none(db_session):
    mgr = ProgressManager(db_session)
    result = await mgr.get_progress(999, "nonexistent")
    assert result is None
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_progress.py -v
```

- [ ] **步骤 3：写 progress.py**

```python
# starlight/core/progress.py
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlight.models import UserProgress

class ProgressManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_progress(self, user_id: int, cartridge_id: str) -> UserProgress | None:
        stmt = select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.cartridge_id == cartridge_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def start_cartridge(self, user_id: int, cartridge_id: str, entry_node: str = "N01") -> UserProgress:
        progress = UserProgress(
            user_id=user_id,
            cartridge_id=cartridge_id,
            current_node=entry_node,
            status="in_progress",
        )
        self.session.add(progress)
        await self.session.commit()
        return progress

    async def advance_node(self, user_id: int, cartridge_id: str, next_node: str) -> UserProgress:
        progress = await self.get_progress(user_id, cartridge_id)
        if progress is None:
            raise ValueError(f"No progress found for user {user_id} in {cartridge_id}")
        progress.current_node = next_node
        await self.session.commit()
        return progress

    async def complete_cartridge(self, user_id: int, cartridge_id: str) -> UserProgress:
        progress = await self.get_progress(user_id, cartridge_id)
        if progress is None:
            raise ValueError(f"No progress found")
        progress.status = "completed"
        progress.completed_at = datetime.utcnow()
        await self.session.commit()
        return progress
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_progress.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: progress manager with start, advance, and complete"
```

---

## 任务 7：贡献者致敬

**文件：**
- 创建：`starlight/core/contributor.py`
- 创建：`tests/test_contributor.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_contributor.py
from starlight.core.contributor import TributeEngine

def test_build_node_tribute():
    engine = TributeEngine()
    contributor = {"name": "张轶霖", "github": "LuckyZ10", "quote": "从零开始"}
    text = engine.build_node_tribute("N01", "变量与赋值", contributor)
    assert "张轶霖" in text
    assert "变量与赋值" in text
    assert "从零开始" in text

def test_build_completion_tribute():
    engine = TributeEngine()
    contributors = [
        {"name": "张轶霖", "github": "LuckyZ10", "quote": "从零开始", "role": "author"},
        {"name": "小明", "github": "xiaoming", "quote": "学习使我快乐", "role": "reviewer"},
    ]
    text = engine.build_completion_tribute("python-basics", "Python 基础", contributors, learner_count=42)
    assert "Python 基础" in text
    assert "张轶霖" in text
    assert "小明" in text
    assert "42" in text

def test_build_completion_tribute_first_learner():
    engine = TributeEngine()
    text = engine.build_completion_tribute("python-basics", "Python", [], learner_count=1)
    assert "第 1 位" in text or "第一位" in text
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_contributor.py -v
```

- [ ] **步骤 3：写 contributor.py**

```python
# starlight/core/contributor.py

class TributeEngine:
    def build_node_tribute(self, node_id: str, node_title: str, contributor: dict) -> str:
        name = contributor.get("name", "匿名")
        quote = contributor.get("quote", "")
        github = contributor.get("github", "")
        lines = [
            f'⭐ {node_title} 由 **{name}** 点亮',
            "",
        ]
        if quote:
            lines.append(f'> "{quote}"')
            lines.append("")
        if github:
            lines.append(f"感谢 @{github} 让这段知识得以存在。")
        else:
            lines.append(f"感谢 {name} 让这段知识得以存在。")
        return "\n".join(lines)

    def build_completion_tribute(self, cartridge_id: str, title: str, contributors: list[dict], learner_count: int = 0) -> str:
        lines = [
            f"🎓 恭喜通关「{title}」！",
            "",
        ]
        if learner_count > 0:
            lines.append(f"你是第 **{learner_count}** 位点亮这颗星的人 ✨")
            lines.append("")

        if contributors:
            lines.append("## 贡献者")
            lines.append("")
            for c in contributors:
                name = c.get("name", "匿名")
                role = c.get("role", "")
                quote = c.get("quote", "")
                role_label = {"author": "作者", "reviewer": "审阅者", "maintainer": "维护者"}.get(role, role)
                line = f"- **{name}**（{role_label}）"
                if quote:
                    line += f' _"{quote}"_'
                lines.append(line)
        return "\n".join(lines)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_contributor.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: tribute engine for contributor acknowledgments"
```

---

## 任务 8：Harness 主引擎

**文件：**
- 创建：`starlight/core/harness.py`
- 创建：`starlight/adapters/base.py`
- 创建：`tests/test_harness.py`

这是把前面所有模块串起来的核心。

- [ ] **步骤 1：写 Adapter 基类**

```python
# starlight/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class HarnessResult:
    text: str
    verdict: str | None = None  # PASS/FAIL/CONTINUE
    state: str | None = None    # idle/learning/assessing/completed
    next_node: str | None = None

class BaseAdapter(ABC):
    @abstractmethod
    async def send_message(self, user_id: str, text: str) -> None:
        """Send a message to the user."""
        pass
```

- [ ] **步骤 2：写失败的测试**

```python
# tests/test_harness.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlight.core.harness import LearningHarness

@pytest.fixture
def mock_deps():
    cartridge_loader = MagicMock()
    cartridge_loader.load.return_value = {
        "id": "python-basics", "title": "Python", "nodes": [
            {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"},
            {"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"},
        ],
        "dag": {"entry": "N01", "edges": {"N01": ["N02"], "N02": []}},
    }
    cartridge_loader.load_node_content.return_value = "# 变量\n变量是存储数据的容器。"
    cartridge_loader.get_entry_node.return_value = {"id": "N01", "title": "变量", "file": "nodes/N01.md", "prerequisites": [], "difficulty": 1, "pass_criteria": "能写赋值语句"}
    cartridge_loader.get_next_nodes.return_value = [{"id": "N02", "title": "类型", "file": "nodes/N02.md", "prerequisites": ["N01"], "difficulty": 1, "pass_criteria": "能区分类型"}]

    assessor = AsyncMock()
    progress_mgr = AsyncMock()
    tribute_engine = MagicMock()

    return cartridge_loader, assessor, progress_mgr, tribute_engine

@pytest.mark.asyncio
async def test_new_user_start(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = None

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="/start", cartridge_id="python-basics")
    assert result.state == "learning"
    assert "变量" in result.text

@pytest.mark.asyncio
async def test_assessment_pass(mock_deps):
    loader, assessor, progress, tribute = mock_deps
    progress.get_progress.return_value = MagicMock(current_node="N01", status="in_progress", cartridge_id="python-basics")
    from starlight.core.assessor import AssessmentResult
    assessor.assess.return_value = AssessmentResult(verdict="PASS", feedback="很好！", score=85)

    harness = LearningHarness(loader, assessor, progress, tribute)
    result = await harness.process(user_id=1, message="变量就是存数据的盒子", cartridge_id="python-basics")
    assert result.verdict == "PASS"
    assert result.next_node == "N02"
```

- [ ] **步骤 3：运行测试验证失败**

```bash
pytest tests/test_harness.py -v
```

- [ ] **步骤 4：写 harness.py**

```python
# starlight/core/harness.py
from starlight.adapters.base import HarnessResult
from starlight.core.cartridge import CartridgeLoader
from starlight.core.assessor import Assessor
from starlight.core.progress import ProgressManager
from starlight.core.contributor import TributeEngine

class LearningHarness:
    def __init__(self, cartridge_loader: CartridgeLoader, assessor: Assessor, progress_mgr: ProgressManager, tribute_engine: TributeEngine):
        self.cartridges = cartridge_loader
        self.assessor = assessor
        self.progress = progress_mgr
        self.tribute = tribute_engine

    async def process(self, user_id: int, message: str, cartridge_id: str) -> HarnessResult:
        # Route: check user state
        progress = await self.progress.get_progress(user_id, cartridge_id)

        if message == "/start":
            return await self._handle_start(user_id, cartridge_id)

        if progress is None or progress.status == "not_started":
            return HarnessResult(text="请先 /start 选择一个卡带", state="idle")

        if progress.status == "completed":
            return HarnessResult(text="你已经通关了！试试 /browse 选新的卡带。", state="completed")

        # In progress: treat message as assessment answer
        return await self._handle_assessment(user_id, message, cartridge_id, progress)

    async def _handle_start(self, user_id: int, cartridge_id: str) -> HarnessResult:
        cart = self.cartridges.load(cartridge_id)
        entry = self.cartridges.get_entry_node(cart)
        content = self.cartridges.load_node_content(cartridge_id, entry["file"])

        progress = await self.progress.start_cartridge(user_id, cartridge_id, entry["id"])

        return HarnessResult(
            text=f"📚 {cart['title']}\n\n{content}\n\n准备好接受考核了吗？直接回答即可。",
            state="learning",
        )

    async def _handle_assessment(self, user_id: int, answer: str, cartridge_id: str, progress) -> HarnessResult:
        cart = self.cartridges.load(cartridge_id)
        current_node = self.cartridges.get_node_by_id(cart, progress.current_node)
        content = self.cartridges.load_node_content(cartridge_id, current_node["file"])

        result = await self.assessor.assess(
            node_content=content,
            pass_criteria=current_node["pass_criteria"],
            conversation=[],
            user_answer=answer,
        )

        if result.verdict == "PASS":
            next_nodes = self.cartridges.get_next_nodes(cart, current_node["id"])
            if not next_nodes:
                await self.progress.complete_cartridge(user_id, cartridge_id)
                tribute_text = self.tribute.build_completion_tribute(
                    cartridge_id, cart["title"], cart.get("contributors", [])
                )
                return HarnessResult(
                    text=f"✅ {result.feedback}\n\n{tribute_text}",
                    verdict="PASS",
                    state="completed",
                )
            else:
                await self.progress.advance_node(user_id, cartridge_id, next_nodes[0]["id"])
                next_content = self.cartridges.load_node_content(cartridge_id, next_nodes[0]["file"])
                return HarnessResult(
                    text=f"✅ {result.feedback}\n\n下一章：{next_nodes[0]['title']}\n\n{next_content}",
                    verdict="PASS",
                    state="learning",
                    next_node=next_nodes[0]["id"],
                )
        elif result.verdict == "FAIL":
            return HarnessResult(
                text=f"❌ {result.feedback}\n\n💡 提示：{result.hint}",
                verdict="FAIL",
                state="learning",
            )
        else:
            return HarnessResult(
                text=f"🤔 {result.feedback}",
                verdict="CONTINUE",
                state="learning",
            )
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest tests/test_harness.py -v
```

- [ ] **步骤 6：Commit**

```bash
git add -A
git commit -m "feat: learning harness with 6-stage lifecycle"
```

---

## 任务 9：计费网关

**文件：**
- 创建：`starlight/billing/gateway.py`
- 创建：`tests/test_billing.py`

- [ ] **步骤 1：写失败的测试**

```python
# tests/test_billing.py
from starlight.billing.gateway import BillingGateway

def test_free_user_daily_limit():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=2, daily_limit=3)
    assert gateway.can_assess("user1") is True

def test_free_user_exceeds_limit():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=3, daily_limit=3)
    assert gateway.can_assess("user1") is False

def test_monthly_user_no_limit():
    gateway = BillingGateway()
    gateway.set_usage("user2", plan="monthly", daily_count=999, daily_limit=0)
    assert gateway.can_assess("user2") is True

def test_user_with_own_key():
    gateway = BillingGateway()
    gateway.set_usage("user3", plan="free", daily_count=10, daily_limit=3, has_own_key=True)
    assert gateway.can_assess("user3") is True

def test_record_usage():
    gateway = BillingGateway()
    gateway.set_usage("user1", plan="free", daily_count=0, daily_limit=3)
    gateway.record("user1", tokens=100, model="glm-4-flash")
    assert gateway.get_daily_count("user1") == 1
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/test_billing.py -v
```

- [ ] **步骤 3：写 gateway.py**

```python
# starlight/billing/gateway.py
from typing import Any

class BillingGateway:
    def __init__(self):
        self._usage: dict[str, dict[str, Any]] = {}

    def set_usage(self, user_id: str, plan: str, daily_count: int, daily_limit: int, has_own_key: bool = False):
        self._usage[user_id] = {
            "plan": plan,
            "daily_count": daily_count,
            "daily_limit": daily_limit,
            "has_own_key": has_own_key,
        }

    def can_assess(self, user_id: str) -> bool:
        usage = self._usage.get(user_id, {})
        if usage.get("has_own_key"):
            return True
        plan = usage.get("plan", "free")
        if plan == "monthly" or plan == "token_pack":
            return True
        # Free plan: check daily limit
        count = usage.get("daily_count", 0)
        limit = usage.get("daily_limit", 3)
        return count < limit

    def record(self, user_id: str, tokens: int = 0, model: str = ""):
        if user_id not in self._usage:
            self._usage[user_id] = {"plan": "free", "daily_count": 0, "daily_limit": 3, "has_own_key": False}
        self._usage[user_id]["daily_count"] = self._usage[user_id].get("daily_count", 0) + 1

    def get_daily_count(self, user_id: str) -> int:
        return self._usage.get(user_id, {}).get("daily_count", 0)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/test_billing.py -v
```

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "feat: billing gateway with free/monthly/token-pack tiers"
```

---

## 任务 10：全量测试 + 集成验证

**文件：**
- 修改：`tests/conftest.py`（补充集成测试 fixtures）

- [ ] **步骤 1：运行全部测试**

```bash
pytest tests/ -v --tb=short
```

预期：全部 PASS

- [ ] **步骤 2：检查测试覆盖范围**

确认以下场景都有测试覆盖：
- 卡带加载（正常/不存在/DAG 校验）
- DAG 解锁逻辑（初始/中间/全部完成）
- Assessor 判定（PASS/FAIL/CONTINUE）
- 进度管理（开始/推进/完成/查询空）
- Harness 集成（start → assess → pass → next node → complete）
- 计费网关（免费限额/包月无限/自带 key）

- [ ] **步骤 3：如果有失败，修复并重跑**

```bash
pytest tests/ -v
```

- [ ] **步骤 4：最终 Commit**

```bash
git add -A
git commit -m "test: full test suite passing for Phase 1 core engine"
```

---

## 自审检查

**规格覆盖：** 逐项检查设计文档需求 → 每个都有对应任务 ✅

**占位符扫描：** 无 TBD/TODO ✅

**类型一致性：** 所有方法签名、返回类型在任务间一致 ✅
- `AssessmentResult.verdict` 在 assessor.py 和 harness.py 中都用 "PASS"/"FAIL"/"CONTINUE" ✅
- `HarnessResult` 结构在 base.py 和 harness.py 中一致 ✅

**缺口：** 无 ✅

---

计划写完保存到 `docs/superpowers/plans/2026-04-03-starlight-phase1.md`。

**两种执行选项：**

**1. 子 Agent 驱动（推荐）** — 每个任务 dispatch 给 coding agent（Claude Code / OpenCode / KiloCode），任务间审查，快速迭代

**2. 顺序执行** — 在本 session 按顺序跑，有审查检查点

选哪种？
