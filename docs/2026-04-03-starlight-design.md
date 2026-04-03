# Project Starlight — 完整设计文档

> 日期：2026-04-03
> 状态：待审查
> 审查人：张轶霖

---

## 一、项目愿景

公开的移动端交互学习平台。"内容开源共编、知识卡带化、Agent 驱动考核"。

核心理念：让知识不再是死的 PDF，而是活的、循序渐进的对话生命体。

## 二、核心决策

| 决策项 | 选择 | 备注 |
|--------|------|------|
| 定位 | 公开平台 | 任何人可创建和消费卡带 |
| 载体 | IM + 轻量 Web | IM 做学习，Web 做编辑和社区 |
| LLM | 国内模型统一 | 默认 GLM（智谱），用户可自带 API key |
| 商业模式 | 包月 + token 包 | 后面再定具体价格 |
| 共编模式 | PR 式审核 + 社区投票 | **后续迭代开发，当前设计预留接口** |
| 架构 | 插件化微内核 | 核心引擎与载体解耦 |
| 扩展性 | 大规模设计，小规模启动 | PostgreSQL 不 SQLite，架构留扩展口 |
| 技术栈 | FastAPI + PostgreSQL + Redis + LiteLLM | |

## 三、架构设计

### 3.1 方案：插件化微内核

```
Starlight Core（核心引擎）
├── Harness（学习引擎）
│   ├── 状态机（6 阶段生命周期）
│   ├── DAG 调度（节点解锁）
│   ├── Assessor（LLM 对话考核）
│   └── 进度管理（持久化、恢复）
├── Cartridge Engine（卡带引擎）
│   ├── .star 格式解析
│   ├── DAG 验证（无环、可达）
│   └── 缓存管理
├── Adapter Layer（适配器）
│   ├── Telegram Adapter（MVP）
│   ├── WeChat Adapter（后续）
│   └── Web Adapter（后续）
├── Billing（计费）
│   ├── 套餐管理
│   ├── 用量追踪
│   └── 自带 API key
├── Community（社区 — 后续开发）
│   ├── PR 式审核
│   ├── 社区投票
│   └── 版本控制
└── Contributor（贡献者）
    ├── 致敬故事
    └── 证书生成
```

### 3.2 数据流

```
用户消息 → Adapter → Harness
                        ├── 1. ROUTE（判断状态）
                        ├── 2. LOAD（加载卡带+节点）
                        ├── 3. TEACH（呈现知识）
                        ├── 4. ASSESS（LLM 考核）
                        ├── 5. JUDGE（PASS/FAIL，更新 DAG）
                        └── 6. TRIBUTE（贡献者致敬）
```

## 四、卡带协议（.star 格式）

### 4.1 文件结构

```
cartridge-id/
├── manifest.json           ← 元数据 + DAG 定义
└── nodes/
    ├── N01-variables.md    ← 节点内容（Markdown）
    ├── N02-types.md
    └── ...
```

### 4.2 manifest.json

```json
{
  "id": "python-basics",
  "title": "Python 基础",
  "version": "1.0.0",
  "language": "zh-CN",
  "contributors": [
    {
      "name": "张轶霖",
      "github": "LuckyZ10",
      "role": "author",
      "bio": "热爱编程的探索者",
      "quote": "每个人都是从 print('hello world') 开始的。",
      "story": "在学习 Python 之前...",
      "location": "中国"
    }
  ],
  "nodes": [
    {
      "id": "N01",
      "title": "变量与赋值",
      "file": "nodes/N01-variables.md",
      "prerequisites": [],
      "difficulty": 1,
      "pass_criteria": "能解释变量赋值的概念并写出基本赋值语句"
    },
    {
      "id": "N02",
      "title": "数据类型",
      "file": "nodes/N02-types.md",
      "prerequisites": ["N01"],
      "difficulty": 1,
      "pass_criteria": "能区分 str/int/float/list 并正确使用"
    }
  ],
  "dag": {
    "entry": "N01",
    "edges": {
      "N01": ["N02"],
      "N02": ["N03"],
      "N03": []
    }
  }
}
```

### 4.3 节点 Markdown 格式

```markdown
# N01: 变量与赋值

## 核心概念
变量是存储数据的容器...

## 示例
​```python
name = "Starlight"
​```

## 常见误区
- 变量名不能以数字开头

---
> 本章节由 **张轶霖** (@LuckyZ10) 贡献
> "每个人都是从 print('hello world') 开始的。"
```

## 五、Harness 学习引擎

### 5.1 核心接口

```python
class LearningHarness:
    """Starlight 学习引擎"""

    async def process(
        self,
        user_id: str,
        message: str,
        context: SessionContext
    ) -> HarnessResult:
        """核心方法：处理一条用户消息，返回学习结果"""
        ...
```

### 5.2 六阶段生命周期

```
1. ROUTE  → 判断用户当前状态（新用户/学习中/考核中/已通关）
2. LOAD   → 加载卡带 + 当前节点内容
3. TEACH  → 向用户呈现知识（Markdown + 重点提取）
4. ASSESS → LLM 驱动的对话考核（核心）
5. JUDGE  → 解析 LLM 输出，PASS/FAIL，更新 DAG
6. TRIBUTE → 通关节点/卡带时，贡献者致敬
```

### 5.3 Assessor 考核引擎

```python
class Assessor:
    async def assess(
        self,
        node: CartridgeNode,
        conversation: list[Message],
        user_answer: str,
        pass_criteria: str,
    ) -> AssessmentResult:
        """
        返回:
        - verdict: PASS / FAIL / CONTINUE
        - feedback: 给用户的反馈
        - score: 理解度 (0-100)
        - hint: 失败时的提示方向
        """
```

### 5.4 LLM System Prompt 策略

```
你是星光学习机的考核官。

考核规则：
1. 基于以下知识内容考核学习者
2. 不要直接问教材里有的问题，而是创设真实场景让学习者应用知识
3. 学习者回答后，判断是否真正理解
4. 判定通过时输出 [PASS]，判定不通过时输出 [FAIL] 并给出提示
5. 如果回答模糊，继续追问（最多3轮），然后必须判定
6. 绝不直接告诉答案，只给方向性提示

知识内容：
{node_content}

通过标准：
{pass_criteria}

当前对话历史：
{conversation}
```

### 5.5 设计原则

| 原则 | 说明 |
|------|------|
| 状态机驱动 | 每个用户会话是状态机，状态保存在 DB，断线可恢复 |
| 考核可插拔 | 预留接口：LLM 对话 / 选择题 / 代码执行 / 人工审核 |
| LLM 无关 | 通过 LiteLLM 抽象，支持任何国内模型 + 用户自带 key |
| 会话隔离 | 每个用户学习会话独立 |
| 可重放 | 所有对话记录保存 |
| 可测试 | 纯 Python，不依赖 IM |

### 5.6 待深度研究（T1 任务）

Harness 的详细实现需要参考启智教学研究成果（24 个教学 skill），包括：
- 苏格拉底对话策略（考核 prompt 设计）
- 认知负荷控制（每节点信息量）
- 自适应难度（动态调整）
- 间隔重复（SM-2，已通关节点复习）
- 学习者模型（能力追踪维度）

详见：`docs/task-harness-research.md`

## 六、Telegram Adapter

### 6.1 指令集

| 指令 | 功能 | Harness 调用 |
|------|------|-------------|
| `/start` | 欢迎 + 注册 | `harness.register()` |
| `/browse` | 浏览可用卡带 | `harness.list_cartridges()` |
| `/play <id>` | 选择卡带开始 | `harness.start_cartridge(id)` |
| `/study` | 进入当前考核 | `harness.begin_assessment()` |
| `/progress` | 查看进度 | `harness.get_progress()` |
| `/review` | 复习已通关节点 | `harness.review()` |
| `/tribute` | 查看贡献者 | `harness.get_tributes()` |
| `/settings` | 设置（API key 等） | `harness.update_settings()` |
| 直接回复文字 | 考核回答 | `harness.submit_answer(text)` |

### 6.2 会话状态路由

```
用户发消息（非 /指令）
  → 在考核中 → 当作回答提交
  → 未在考核 → 提示 /study
  → 未选卡带 → 提示 /browse
  → 新用户   → 提示 /start
```

### 6.3 消息格式

| 场景 | 格式 |
|------|------|
| 知识呈现 | Markdown |
| 考核反馈 | ✅ PASS / ❌ FAIL + 文字反馈 |
| 进度展示 | `[██░░░░░░] 2/8` |
| 贡献者致敬 | 名字 + 格言 + 感谢 |
| 证书 | 文字（后续可加图片） |

## 七、计费系统

### 7.1 用户分层

| 层级 | 免费版 | 包月版 | Token 包 |
|------|--------|--------|----------|
| 月费 | ¥0 | 待定 | 按量购买 |
| 每日考核 | 3次/天 | 不限 | 不限 |
| 可用卡带 | 标记免费的 | 全部 | 全部 |
| LLM | 基础模型 | 高级模型 | 自选 |
| 进度保存 | 7 天 | 永久 | 永久 |
| 自带 API key | ❌ | ✅ | ✅ |

### 7.2 计费路由

```
优先级：
1. 用户自带 API key → 用用户的，平台不收费
2. Token 包 → 扣包里的量
3. 包月 → 扣包月额度
4. 免费 → 扣免费额度（3次/天）
```

### 7.3 LLM 模型

统一使用国内模型（智谱 GLM 系列）。不接入海外模型。

## 八、共编平台（后续迭代）

> ⚠️ 此模块为后续开发，当前只做设计预留。

### 8.1 角色

| 角色 | 权限 |
|------|------|
| 浏览者 | 查看、学习、点赞 |
| 贡献者 | Fork 卡带、提交 PR |
| 审阅者 | 投票 +1/-1、写评审 |
| 维护者 | 合并 PR、锁定版本 |
| 管理员 | 删除/下架、任命 |

### 8.2 审核流程

```
PR 提交 → 自动校验 → 7 天投票期 → ≥3 人投票 → ≥70% 赞成 → 维护者合并
```

### 8.3 自动校验项

- manifest.json 格式正确
- 所有 node 文件存在且非空
- DAG 无环（拓扑排序）
- 所有节点可达
- prerequisites 引用有效
- 每节点 ≤ 2000 字
- pass_criteria 非空
- 贡献者信息完整

### 8.4 初期策略

MVP 阶段用 **GitHub 仓库** 管理卡带，天然支持版本控制和 PR 审核。Web 编辑器后续再加。

## 九、贡献者致敬（Tribute System）

### 9.1 触发时机

| 时机 | 内容 |
|------|------|
| 通关节点 | 作者名字 + 格言 |
| 通关卡带 | 完整贡献者名单 + 每人故事 |
| 首次通关 | "你是第 X 位点亮这颗星的人" |
| 复习时 | 随机展示贡献者趣事 |

### 9.2 致敬文案生成

通关时由 LLM 生成有温度的文案（非模板）：

```
⭐ 第 3 章「数据类型」由 张轶霖 点亮

"每个人都是从 print('hello world') 开始的。"

感谢 @LuckyZ10 让这段知识得以存在。
```

### 9.3 排行榜维度

- 贡献节点数
- 被学习次数
- 节点通过率（讲得好不好）
- 社区投票活跃度

## 十、数据模型

### 10.1 核心表

```sql
-- 用户
users (id, telegram_id, name, plan, api_key_enc, created_at)

-- 卡带
cartridges (id, title, version, language, entry_node, created_by, status)

-- 节点
nodes (id, cartridge_id, title, file_path, prerequisites, difficulty, pass_criteria)

-- 用户进度
user_progress (user_id, cartridge_id, current_node, status, started_at, completed_at)

-- 考核记录
assessments (id, user_id, node_id, verdict, score, messages_json, created_at)
```

### 10.2 贡献者

```sql
-- 贡献者
contributors (id, name, github, location, bio, quote, story, joined_at)

-- 卡带-贡献者关联
cartridge_contributors (cartridge_id, contributor_id, role)
```

### 10.3 计费

```sql
-- 套餐
plans (id, name, price_monthly, daily_limit, model_access, features_json)

-- 用量日志
usage_log (user_id, action, tokens_used, model_used, created_at)

-- API Key
api_keys (user_id, provider, api_key_enc, created_at)
```

### 10.4 共编（后续）

```sql
-- PR
prs (id, cartridge_id, author_id, status, changes_json, created_at, merged_at)

-- 投票
votes (pr_id, user_id, vote, created_at)

-- 评审
reviews (pr_id, user_id, comment, verdict, created_at)
```

## 十一、待研究 & 待决策

| # | 任务 | 状态 |
|---|------|------|
| T1 | Harness 深度设计（参考启智 24 个 skill） | 任务书已写 |
| T2 | 卡带协议 Schema 细化 | 待开始 |
| T3 | 数据库 DDL 详细设计 | 待开始 |
| T4 | Web API 路由设计 | 待开始 |
| T5 | 共编审核机制详细方案 | 后续 |
| T6 | **卡带制造 Agent** — 自动/半自动生成卡带 | 后续，方式待定 |
| T7 | 包月/token 包定价 | 后续 |
| T8 | Telegram Bot 注册流程（BotFather） | 待开始 |

## 十二、开发路线图

### Phase 0: 设计规划（当前）
- [x] 项目愿景和核心决策
- [x] 架构方案
- [x] 全部 7 个模块设计
- [ ] Harness 深度研究
- [ ] Schema / DDL / API 细化

### Phase 1: 核心引擎
- Harness 实现
- 卡带引擎
- DAG 调度
- 进度持久化

### Phase 2: Telegram 入口
- Bot 注册
- Adapter 实现
- 完整闭环测试

### Phase 3: 示例卡带
- 1-2 个完整卡带
- 端到端测试

### Phase 4: Web 平台
- REST API
- 卡带编辑器
- 用户仪表盘

### Phase 5: 社区 & 计费
- 共编平台（PR 审核 + 投票）
- 套餐 + token 包计费
- 自带 API key

### Phase 6: 扩展
- 微信支持
- 卡带制造 Agent
- 更多考核模式
- 排行榜、成就系统

## 十三、参考资源

- 启智教学研究成果：`~/.openclaw/workspace-agents/mentor/skills/`（24 个 skill）
- 启智进化报告：`~/.openclaw/workspace/learning/teaching-skill/evolution-report.md`
- Harness 研究任务书：`docs/task-harness-research.md`
