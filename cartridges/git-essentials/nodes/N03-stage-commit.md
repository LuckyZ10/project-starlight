# 暂存与提交

## 核心概念

Git 的工作流程可以概括为三步：**修改 → 暂存 → 提交**。这一节我们学习如何把你的修改记录到版本历史中。

## git add — 暂存更改

把工作区的修改放入暂存区（"购物车"）：

```bash
# 暂存单个文件
git add hello.py

# 暂存多个文件
git add main.py utils.py

# 暂存当前目录下所有修改的文件
git add .

# 暂存所有修改（包括整个仓库）
git add -A
```

`git add` 不会修改文件本身，只是告诉 Git："下次提交时，请包含这个文件当前的修改。"

**取消暂存**（把文件从暂存区移回工作区，不丢失修改）：

```bash
git restore --staged hello.py
# 旧语法：git reset HEAD hello.py
```

## git commit — 提交更改

把暂存区的内容正式记录为一个提交：

```bash
# 提交并写提交信息
git commit -m "添加用户登录功能"

# 打开编辑器写更详细的提交信息
git commit

# 跳过暂存步骤，直接提交所有已追踪文件的修改
git commit -a -m "修复拼写错误"
```

每次提交都会生成一个唯一的哈希 ID（如 `7f3a2b1`），记录：
- 谁做的修改（作者信息）
- 什么时候做的（时间戳）
- 修改了什么（文件差异）
- 为什么修改（提交信息）

## 写好提交信息

好的提交信息让项目历史清晰可读：

```bash
# ✅ 好的提交信息
git commit -m "feat: 添加用户注册 API"
git commit -m "fix: 修复登录时密码验证失败的问题"
git commit -m "docs: 更新 README 安装说明"

# ❌ 不好的提交信息
git commit -m "修改"
git commit -m "fix bug"
git commit -m "update"
```

推荐的格式（Conventional Commits）：
```
<类型>: <简短描述>

[可选的详细说明]
```

常见类型：`feat`（新功能）、`fix`（修复）、`docs`（文档）、`refactor`（重构）、`test`（测试）

## git log — 查看历史

```bash
# 查看提交历史
git log

# 简洁格式（一行一个提交）
git log --oneline

# 查看最近 5 条
git log --oneline -5

# 查看文件修改的统计信息
git log --stat

# 图形化显示分支
git log --oneline --graph --all
```

## git diff — 查看差异

```bash
# 工作区 vs 暂存区（还没 add 的修改）
git diff

# 暂存区 vs 最近提交（add 了但还没 commit 的修改）
git diff --staged

# 两个提交之间的差异
git diff abc123 def456
```

## 常见误区

1. **提交太大**：一个提交包含十几个不相关的修改，难以 review 和回滚。尽量做到"一个提交一个逻辑变更"。
2. **忘记 add 就 commit**：新建的文件必须先 `git add`，否则 `git commit` 不会包含它。已追踪文件的修改可以用 `git commit -a` 跳过 add。
3. **提交敏感信息**：密码、API Key 等一旦提交进历史，即使后续删除也能在历史中找到。应该用 `.gitignore` 排除敏感文件。
4. **提交信息写"修改了一些东西"**：一周后你自己都看不懂。提交信息应该说明"做了什么"和"为什么"。
