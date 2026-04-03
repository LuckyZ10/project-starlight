# Project Starlight (星光学习机)

> "让知识不再是死的 PDF，而是活的、循序渐进的对话生命体。"

## 项目定位

公开的移动端交互学习平台。内容开源共编、知识卡带化、Agent 驱动考核。

## 核心决策

| 决策 | 选择 |
|------|------|
| 定位 | 公开平台 |
| 载体 | IM（Telegram 优先）+ 轻量 Web（编辑/社区） |
| LLM | 默认 GLM（智谱），用户可自带 API key |
| 商业模式 | 基本包月费 + 叠加 token 包 |
| 共编模式 | PR 式审核 + 社区投票（质量第一） |
| 架构 | 插件化微内核（方案 A） |
| 扩展性 | 大规模设计，小规模启动 |
| 技术栈 | FastAPI + PostgreSQL + Redis + LiteLLM |

## 架构概览

```
Starlight Core（核心引擎）
├── Harness（学习引擎）— 最核心的模块
│   ├── 状态机（用户会话管理）
│   ├── DAG 调度（节点解锁）
│   ├── Assessor（LLM 对话考核）
│   └── 进度管理（持久化、恢复）
├── Cartridge Engine（卡带引擎）
│   ├── .star 格式解析
│   ├── DAG 验证
│   └── 缓存管理
├── Adapter Layer（适配器）
│   ├── Telegram Adapter
│   ├── WeChat Adapter（后续）
│   └── Web Adapter（REST API + 前端）
├── Billing（计费）
│   ├── 套餐管理
│   ├── 用量追踪
│   └── 自带 API key
├── Community（社区）
│   ├── PR 式审核
│   ├── 社区投票
│   └── 版本控制
└── Contributor（贡献者）
    ├── 致敬故事
    └── 证书生成
```

## 卡带协议（.star 格式）

```
cartridge-id/
├── manifest.json    ← 元数据 + DAG 定义
└── nodes/
    ├── N01-xxx.md   ← 节点内容（Markdown）
    └── ...
```

## Harness 6 阶段生命周期

```
1. ROUTE  → 判断用户状态
2. LOAD   → 加载卡带 + 节点
3. TEACH  → 呈现知识
4. ASSESS → LLM 对话考核（核心）
5. JUDGE  → PASS/FAIL 判定，更新 DAG
6. TRIBUTE → 贡献者致敬
```

## 待研究任务

- [ ] **T1: Harness 深度设计** — 参考启智研究成果（24个教学skill），设计考核引擎的详细实现
- [ ] **T2: 卡带制造 Agent** — 自动/半自动生成卡带内容
- [ ] **T3: 共编审核机制** — 研究成熟的开源协作方案
- [ ] **T4: 计费系统** — 包月 + token 包的定价和实现

## 启智研究成果参考

启智（mentor agent）已完成 24 个教学 skill 的研究，涵盖：

### 教学方法论（12个）
1. 费曼学习法 — 用简单语言解释
2. 间隔重复（SM-2）— 艾宾浩斯遗忘曲线
3. 主动回忆 — 主动提取记忆
4. 认知负荷理论 — 优化信息呈现
5. 交替学习 — 交替不同类型内容
6. 元认知策略 — 教会"如何学习"
7. 建构主义 — 主动构建知识
8. 最近发展区（ZPD）— 最佳学习区域
9. 脚手架教学 — 逐步撤除支持
10. 协作学习 — 通过互动构建知识
11. 游戏化学习 — XP/徽章/排行榜
12. SM-2 算法 — 科学的复习间隔

### 模块体系
- adaptive-learning（自适应学习）
- assessment（评估）
- cognitive-load（认知负荷）
- concept-connector（概念连接）
- content-adaptor（内容适配）
- course-design（课程设计）
- difficulty-adjuster（难度调整）
- error-analyzer（错误分析）
- example-generator（示例生成）
- explanation-optimizer（解释优化）
- feedback-system（反馈系统）
- gamification（游戏化）
- knowledge-graph（知识图谱）
- learner-model（学习者模型）
- lesson-templates（课程模板）
- metacognition-prompt（元认知）
- motivation-tracker（动机追踪）
- progress-visualizer（进度可视化）
- question-design（题目设计）
- review-scheduler（复习调度）
- socratic-dialogue（苏格拉底对话）
- spaced-repetition（间隔重复）
- study-planner（学习计划）
- teaching-methods（教学方法）

这些 skill 的源文件位于：
`~/.openclaw/workspace-agents/mentor/skills/`
