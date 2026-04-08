# Starlight Web — Phase 1: 响应式布局 + 移动端优化

## 目标
让 Starlight Web 在**手机、平板、桌面**三个设备上都能丝滑运行，提供一致的学习体验。

---

## 响应式断点

```css
/* 大屏幕桌面 (>1024px) */
@media (min-width: 1025px) {
  - 三栏布局
  - 节点列表固定宽度
  - 对话区自适应宽度
  - 知识图谱悬浮在右侧
}

/* 平板 (768px - 1024px) */
@media (max-width: 1024px) and (min-width: 769px) {
  - 两栏布局
  - 节点列表变窄
  - 知识图谱收起/折叠
}

/* 手机 (<768px) */
@media (max-width: 768px) {
  - 单栏布局
  - 顶部固定标题栏
  - 底部固定导航栏
  - 节点列表改为抽屉式侧边栏
}
```

---

## 布局方案

### 1. 桌面版 (>1024px)
```
┌──────────┬──────────────────────┬──────────┐
│          │  [对话区/聊天]        │          │
│ 节点列表  │                      │ [图谱]   │
│ (280px)  │                      │ (浮动)   │
│          │                      │          │
│ ✅ N01   │  AI: 今天我们学习...  │          │
│ ✅ N02   │  [题目卡片弹出]       │          │
│ 🔄 N03   │  [推理卡片]           │          │
│ ...      │                      │          │
│          │                      │          │
│ [图谱]   │                      │          │
└──────────┴──────────────────────┴──────────┘
```

### 2. 平板版 (768px - 1024px)
```
┌──────────┬──────────────────────────────┐
│          │  [对话区/聊天]                │
│ 节点列表  │                              │
│ (240px)  │  AI: 今天我们学习...          │
│          │  [题目卡片弹出]               │
│          │  [推理卡片]                   │
│          │                              │
│          │                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

### 3. 手机版 (<768px)
```
┌─────────────────────────┐
│ N01 自监督学习  1/33 ▼   │ ← 顶部固定
├─────────────────────────┤
│                         │
│ AI: 今天我们学习...      │
│ [对话区滚动]             │
│                         │
│ [题目卡片弹出]           │
│ [推理卡片]               │
│                         │
│ [自动回复输入框]         │
├─────────────────────────┤
│ [聊天] [图谱] [统计]     │ ← 底部固定
└─────────────────────────┘
```

---

## 移动端设计细节

### 1. 导航栏

**底部导航栏**（手机）：
```tsx
const MobileNavBar = () => (
  <div className="mobile-nav">
    <button>聊天</button>
    <button>图谱</button>
    <button>统计</button>
    <button>设置</button>
  </div>
);

// 样式
.mobile-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 100;
}

.mobile-nav button {
  flex: 1;
  height: 100%;
  font-size: 14px;
  color: var(--text-muted);
}

.mobile-nav button.active {
  color: var(--accent);
}
```

**桌面悬浮导航**（桌面）：
- 固定在右侧（宽度 60px）
- 图标样式
- 鼠标悬停显示标签

### 2. 节点列表（手机）

**抽屉式侧边栏**（点击"节点列表"按钮打开）：
```
┌─────────────────────┐
│ ☰ N01 自监督学习     │
│ ✅ N02 监督学习      │
│ ✅ N03 损失函数      │
│ 🔄 N04 梯度下降      │
│ ...                 │
└─────────────────────┘
```

**实现方式**：
- 使用 React Portal
- 全屏遮罩（rgba(0,0,0,0.5)）
- 手势：左滑关闭、右滑打开

### 3. 输入框（手机）

**自适应高度输入框**：
```tsx
const MobileInput = () => {
  const [height, setHeight] = useState(60);

  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const textarea = e.currentTarget;
    textarea.style.height = '60px';
    textarea.style.height = `${textarea.scrollHeight}px`;
  };

  return (
    <textarea
      style={{
        height: `${Math.max(60, height)}px`,
        minHeight: '60px',
        maxHeight: '150px',
      }}
      onInput={handleInput}
    />
  );
};
```

**防软键盘遮挡**：
- 输入框始终在可见区域
- 输入时自动滚动到可见区

### 4. 按钮（手机）

**最小点击区域**：44x44px（iOS 标准）
```tsx
const MobileButton = ({ children, ...props }) => (
  <button
    {...props}
    style={{
      minHeight: '44px',
      minWidth: '44px',
      fontSize: '16px',
    }}
  >
    {children}
  </button>
);
```

### 5. 下拉刷新

**下拉刷新学习记录**：
```tsx
const usePullToRefresh = (onRefresh: () => Promise<void>) => {
  const [pulling, setPulling] = useState(false);
  const [y, setY] = useState(0);

  const onTouchStart = (e: React.TouchEvent) => {
    setY(e.touches[0].clientY);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    const diff = e.touches[0].clientY - y;
    if (diff > 0 && diff < 100) {
      setPulling(true);
    }
  };

  const onTouchEnd = async (e: React.TouchEvent) => {
    const diff = e.changedTouches[0].clientY - y;
    if (diff > 60) {
      await onRefresh();
    }
    setPulling(false);
  };

  return { pulling, onTouchStart, onTouchMove, onTouchEnd };
};
```

---

## 丝滑动画

### 1. 题目卡片弹出
```css
.question-card {
  animation: popIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes popIn {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
```

### 2. 推理卡片展开
```css
.reasoning-steps {
  transition: height 0.3s ease-out;
  overflow: hidden;
}

.reasoning-steps.expanded {
  height: auto;
}
```

### 3. 聊天消息滑入
```css
.message {
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  0% {
    transform: translateY(20px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
}
```

### 4. 页面切换过渡
```tsx
import { motion } from 'framer-motion';

const AnimatedPage = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
);
```

---

## 性能优化

### 1. 懒加载组件
```tsx
// 路由级别懒加载
const GraphComponent = dynamic(
  () => import('@/components/knowledge-graph'),
  { ssr: false }
);

// 组件级别懒加载
const GraphView = dynamic(
  () => import('./graph-view'),
  { loading: () => <Skeleton /> }
);
```

### 2. 虚拟滚动（聊天消息列表）
```tsx
import { FixedSizeList } from 'react-window';

const ChatMessageList = ({ messages }) => (
  <FixedSizeList
    height={600}
    itemCount={messages.length}
    itemSize={120}
    width="100%"
  >
    {({ index, style }) => (
      <MessageItem style={style} message={messages[index]} />
    )}
  </FixedSizeList>
);
```

### 3. 图片懒加载
```tsx
<img loading="lazy" src={url} alt="..." />
```

### 4. 防抖/节流
```tsx
import { useDebouncedCallback, useThrottledCallback } from 'use-debounce';

const debouncedSearch = useDebouncedCallback(
  (value) => searchNodes(value),
  300
);

const throttledPull = useThrottledCallback(
  () => pullToRefresh(),
  1000
);
```

---

## 移动端设备检测

### 方案 1：CSS 媒体查询（推荐）
```css
/* 手机端专属样式 */
@media (max-width: 768px) {
  .desktop-only {
    display: none;
  }

  .mobile-full {
    width: 100% !important;
    height: 100vh !important;
  }
}
```

### 方案 2：JavaScript Hook
```tsx
import { useMediaQuery } from 'react-responsive';

const isMobile = useMediaQuery('(max-width: 768px)');
const isTablet = useMediaQuery('(max-width: 1024px)');

return (
  <div className={isMobile ? 'mobile-layout' : 'desktop-layout'}>
    {/* 根据设备显示不同组件 */}
  </div>
);
```

### 方案 3：设备检测库
```tsx
import { isMobile } from 'react-device-detect';

if (isMobile) {
  // 移动端逻辑
}
```

---

## 兼容性

### 支持的浏览器
- Chrome 90+
- Safari 14+
- Firefox 88+
- Edge 90+

### Polyfill（如需要）
```tsx
// 使用 @vitejs/plugin-legacy
{
  plugins: [
    legacy({
      targets: ['> 0.5%', 'not dead', 'last 2 versions']
    })
  ]
}
```

---

## 移动端性能指标

### 目标
- **首次内容绘制 (FCP)**: < 1.5s
- **累积布局偏移 (CLS)**: < 0.1
- **首次输入延迟 (FID)**: < 100ms
- **最大内容绘制 (LCP)**: < 2.5s

### 优化手段
1. **预加载关键资源**：
```html
<link rel="preload" href="/fonts/inter.woff2" as="font" />
```

2. **减少重绘/回流**：
```css
/* 使用 transform 和 opacity 动画 */
.question-card {
  transform: scale(0.8);
  opacity: 0;
}
```

3. **代码分割**：
```js
// 路由级代码分割
const LoginPage = lazy(() => import('./login'));
const LearnPage = lazy(() => import('./learn/[cartridgeId]'));
```

---

## 实现步骤

### 后端（无需修改）
- ✓ 所有 API 兼容手机端
- ✓ 响应式布局只需前端处理

### 前端（需要修改）

**Phase 1.1：响应式布局**
1. 修改 `Layout.tsx` - 添加断点响应
2. 修改 `learn/[cartridgeId]/page.tsx` - 三栏/两栏/单栏
3. 修改 `components/knowledge-graph.tsx` - 移动端适配

**Phase 1.2：移动端导航**
1. 创建 `MobileNavBar.tsx` - 底部导航栏
2. 修改桌面导航 - 悬浮样式

**Phase 1.3：移动端交互**
1. 创建 `Drawer.tsx` - 抽屉式侧边栏
2. 实现手势（左滑关闭、右滑打开）
3. 创建 `MobileInput.tsx` - 自适应高度输入框

**Phase 1.4：移动端优化**
1. 添加下拉刷新
2. 优化按钮点击区域（44x44px）
3. 防软键盘遮挡

**Phase 1.5：动画优化**
1. 引入 Framer Motion
2. 添加弹出/展开动画
3. 添加页面切换过渡

**Phase 1.6：性能优化**
1. 组件懒加载
2. 聊天消息虚拟滚动
3. 图片懒加载
4. 防抖/节流

---

## 测试清单

### 设备测试
- [ ] iPhone SE (375x667)
- [ ] iPhone 14 Pro (393x852)
- [ ] iPad Pro (1024x1366)
- [ ] iPad Mini (744x1133)
- [ ] 桌面 1920x1080
- [ ] 桌面 2560x1440

### 功能测试
- [ ] 导航栏在手机端正常显示
- [ ] 节点列表在手机端可展开/收起
- [ ] 输入框在手机端自适应高度
- [ ] 下拉刷新正常工作
- [ ] 题目卡片弹出动画流畅
- [ ] 页面切换过渡平滑

### 性能测试
- [ ] Lighthouse 性能评分 > 80
- [ ] 聊天消息列表滚动流畅（50+条消息）
- [ ] 页面切换无明显卡顿

---

## 后续阶段（可选）

**Phase 2：性能优化**
- Service Worker（离线缓存）
- PWA 安装提示
- 高级手势（长按菜单、滑动操作）

**Phase 3：丝滑体验**
- VR/AR 适配
- 动画特效
- 声音反馈

---

## 技术栈补充

**需要安装的依赖**：
```bash
npm install framer-motion react-window react-device-detect use-debounce
```

**CSS 工具类库**（可选）：
- Tailwind CSS（已有）
- clsx（条件样式）
- tailwind-merge（合并 Tailwind 类名）

---

## 注意事项

1. **移动端优先**：手机体验优先保证，然后适配桌面
2. **触摸交互**：移动端使用触摸事件，桌面使用鼠标事件
3. **性能监控**：使用 React Profiler 检测性能瓶颈
4. **A/B 测试**：不同设备可能需要不同的交互方式

---

## 示例代码

### 完整的响应式布局组件
```tsx
export default function ResponsiveLayout({ children }) {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const isTablet = useMediaQuery('(max-width: 1024px)');

  return (
    <div className={isMobile ? 'mobile-layout' : isTablet ? 'tablet-layout' : 'desktop-layout'}>
      {isMobile && <MobileNavBar />}

      <main className="content">
        {children}
      </main>

      {isMobile && <MobileDrawer />}
    </div>
  );
}
```

### 按钮组件（移动端友好）
```tsx
export default function MobileButton({
  children,
  onClick,
  ...props
}) {
  return (
    <button
      onClick={onClick}
      style={{
        minHeight: '44px',
        minWidth: '44px',
        fontSize: '16px',
        padding: '0 16px',
      }}
      {...props}
    >
      {children}
    </button>
  );
}
```

---

## 总结

**Phase 1 核心目标**：
1. ✅ 响应式布局（手机/平板/桌面）
2. ✅ 移动端导航（底部栏 + 抽屉式侧边栏）
3. ✅ 移动端交互优化（输入框、手势、下拉刷新）
4. ✅ 丝滑动画（弹出、展开、过渡）
5. ✅ 性能优化（懒加载、虚拟滚动、防抖）

**预计时间**：2-3 天

**风险**：
- 低：主要是 UI 调整，不涉及业务逻辑
- 缓解：使用现有设计系统，复用组件
