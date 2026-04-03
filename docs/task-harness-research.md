# Task: Harness 深度设计研究

## 目标
设计 Starlight 项目中最核心的模块——Learning Harness（学习引擎）。

## 研究素材

### 1. 启智（mentor）教学研究成果
启智是一个专门研究教学方法的 AI agent，已完成 24 个教学 skill：

位置：`~/.openclaw/workspace-agents/mentor/skills/`

关键 skill（对 Harness 最有参考价值）：
- `assessment/` — 评估体系（如何判断"学会了"）
- `socratic-dialogue/` — 苏格拉底式对话（通过提问引导思考）
- `cognitive-load/` — 认知负荷（控制信息密度）
- `adaptive-learning/` — 自适应学习（根据水平调整难度）
- `difficulty-adjuster/` — 难度调整（动态调节）
- `feedback-system/` — 反馈系统（给学生的反馈策略）
- `learner-model/` — 学习者模型（画像和能力追踪）
- `spaced-repetition/` — 间隔重复（SM-2 算法，复习调度）
- `knowledge-graph/` — 知识图谱（概念之间的关系）
- `gamification/` — 游戏化（XP、徽章、排行榜）
- `error-analyzer/` — 错误分析（诊断误解）
- `question-design/` — 题目设计（生成好问题的方法）

### 2. 项目设计文档
`/tmp/project-starlight/README.md`

### 3. 已确认的设计决策
- Harness 不依赖任何 IM 框架（纯 Python）
- 通过 6 阶段生命周期处理学习流程
- Assessor 是核心（LLM 对话考核）
- 状态机驱动，支持断线恢复
- 考核方式可插拔（LLM 对话 / 选择题 / 代码执行 / 人工审核）
- 通过 LiteLLM 支持多种 LLM

## 输出要求

### 需要回答的问题
1. **状态机设计**：用户会话的完整状态转换图
2. **Assessor 深度设计**：
   - 如何构建考核 prompt（参考苏格拉底对话 skill）
   - 如何判断 PASS/FAIL（评分标准、多轮判定策略）
   - 如何处理模糊回答（追问策略）
   - 如何防止作弊（背诵教材原文）
3. **认知负荷控制**：每次呈现多少知识合适
4. **自适应难度**：如何根据用户表现动态调整考核难度
5. **间隔重复集成**：已通关节点的复习策略（SM-2）
6. **学习者模型**：追踪哪些维度，如何影响考核策略

### 输出文件
- `/tmp/project-starlight/docs/harness-design.md` — 完整的 Harness 设计文档
  - 状态机图（ASCII 或 mermaid）
  - Assessor 的 prompt 模板
  - 评分算法
  - 代码接口定义（Python protocol/class）

## 约束
- 质量优先，不要急着写代码
- 深入阅读启智的每个相关 skill，提取可用的设计模式
- 引用启智 skill 中的具体方法和算法，不要泛泛而谈
