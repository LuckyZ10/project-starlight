# Starlight Web v2 — 交互式学习 + Game Boy 清爽风

## 视觉风格：轻像素 Game Boy / Switch

### 配色
- bg-primary: #f0f4f0 (淡绿灰)
- bg-card: #ffffff (白)
- accent: #2d6a4f (深森林绿)
- accent-light: #52b788 (翠绿)
- accent-hover: #40916c
- text-primary: #1b4332
- text-secondary: #52796f
- text-muted: #8db48e
- border: #2d6a4f
- border-light: #b7e4c7
- success: #52b788
- warning: #ffd166
- error: #ef476f

### 字体
- 标题: 'JetBrains Mono', 'Fira Code', monospace
- 正文: 'Inter', system-ui, sans-serif
- 代码/公式: 'JetBrains Mono', monospace

### 组件风格
- 卡片: 白底 + 2px solid #2d6a4f + 4px 圆角 + 微妙阴影
- 按钮: 2px 实线边框 + hover 时绿色填充白字
- 输入框: 白底 + 2px 边框 + focus 时翠绿高亮
- 状态图标: 🟩已完成 🟨学习中 ⬜未开始
- 题目卡片: 像素风边框 + 绿色选中态

---

## 技术栈
- Backend: FastAPI + SQLite + JWT + SSE streaming
- Frontend: Next.js 14 + Tailwind CSS + Zustand
- LLM: GLM-5.1 via Anthropic compatible API
- 图谱: React Flow

---

## 功能清单

### 1. 认证
- 邮箱+密码注册/登录
- JWT token, 7天过期
- 未登录可浏览，学习时弹登录框

### 2. Landing 页 (/)
- 卡带卡片网格
- 每张卡: 标题 + 节点数 + 难度 + 预估时间
- Game Boy 卡带风格（绿色边框 + 像素标题）

### 3. 学习页 (/learn/{cartridgeId})
左栏 (280px):
- 进度条 (绿色填充)
- 节点列表: 🟩🟨⬜ 状态
- 图谱切换按钮

右栏 (主区域):
- 对话流: AI 消息 + 题目卡片交替
- AI 消息支持 Markdown + KaTeX
- 流式输出 (SSE)

### 4. 四种题目卡片
单选题: 选项列表, 单选, 提交
多选题: 选项列表, 多选, 已选计数
填空题: 文本输入框, 模糊匹配
判断题: 对/错 两个按钮

### 5. 推理卡片
- 折叠/展开步骤
- 每步可展开详情
- 默认折叠

### 6. 答题反馈
- 答对: ✅ + 关键点总结
- 答错: ❌ + 💡提示 + 重试
- 连续3次错: 推荐基础知识点

### 7. 难度调整
- 记录答题历史
- 答错率>70%: 降难度
- 连续答对: 进阶题

---

## LLM 对话协议

### System Prompt
```
你是 Starlight 学习系统的 AI 导师。
当前卡带: {cartridge_title}
当前节点: {node_title}
知识点列表: {kp_list}
通过标准: {pass_criteria}

教学规则:
1. 友好但专业，不要废话
2. 用苏格拉底式提问引导思考
3. 讲完一个知识点后自动出一道题
4. 题目类型轮换: 单选→判断→多选→填空
5. 答错给提示，连续答错推荐基础
6. 用 Markdown 格式，公式用 $...$

题目输出格式 (严格 JSON):
当需要出题时，在消息末尾输出:
<<QUESTION>>
{"type":"single_choice","question":"...","options":["A","B","C","D"],"answer":1,"explanation":"..."}
<</QUESTION>>

type 可选: single_choice, multi_choice, fill_blank, judgment
判断题: {"type":"judgment","statement":"...","answer":true,"explanation":"..."}
多选题: {"type":"multi_choice","question":"...","options":["A","B","C"],"answers":[0,2],"explanation":"..."}
填空题: {"type":"fill_blank","question":"...","answer":"关键词","explanation":"..."}

推理步骤输出格式:
<<REASONING>>
{"title":"推理过程","steps":[{"title":"第1步","content":"..."},{"title":"第2步","content":"..."}]}
<</REASONING>>
```

### 前端解析
1. 流式接收文本
2. 检测 `<<QUESTION>>...<</QUESTION>>` 标签
3. 解析 JSON 渲染题目卡片
4. 检测 `<<REASONING>>...<</REASONING>>` 标签
5. 解析 JSON 渲染推理卡片
6. 其余文本正常 Markdown 渲染

### 答题后流程
用户提交答案 → POST /api/learning/answer → AI 根据对错继续对话

---

## API Endpoints

POST /api/auth/register
POST /api/auth/login
GET /api/auth/me
GET /api/cartridges
GET /api/cartridges/{id}
GET /api/cartridges/{id}/nodes/{nodeId}
POST /api/learning/chat → SSE stream
POST /api/learning/answer → {correct, feedback, next_question?}
GET /api/learning/progress/{cartridgeId}
POST /api/learning/complete

---

## 响应式 (Phase 1)
- 桌面 (>1024px): 三栏
- 平板 (768-1024px): 两栏
- 手机 (<768px): 单栏 + 底部导航

---

## 开发步骤

### Step 1: Backend 基础 (Claude Code, 180s)
- FastAPI app + SQLite models + JWT auth
- Cartridge/node 读取 API
- 启动: port 8000

### Step 2: Backend 聊天 (Claude Code, 180s)
- SSE streaming chat endpoint
- Answer submission endpoint
- Progress tracking

### Step 3: Frontend 骨架 (Claude Code, 180s)
- Next.js + Tailwind + Game Boy 主题
- Landing + Login + Register 页
- 基础布局

### Step 4: Frontend 学习页 (Claude Code, 180s)
- 左栏节点列表 + 进度条
- 右栏对话区 + 流式输出
- 题目卡片 + 推理卡片组件

### Step 5: 响应式 (Claude Code, 180s)
- 手机/平板/桌面适配
- 底部导航栏
- 抽屉式侧边栏

### Step 6: 整合测试 (Moly)
- 启动两端
- 端到端测试
- 截图给 Kilocode 审查
