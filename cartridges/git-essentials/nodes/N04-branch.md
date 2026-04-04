# 分支

## 核心概念

分支是 Git 最强大的功能之一。**分支让你在不影响主线的情况下开发新功能、修复 bug 或做实验。** 想象一棵树：主干是稳定版本，树枝是各种尝试。

在 Git 中，分支本质上只是一个指向某个提交的**可移动指针**。创建分支非常轻量——只是创建了一个新指针，不是复制文件。

## 默认分支

Git 初始化时会自动创建一个默认分支。以前叫 `master`，现在社区推荐用 `main`：

```bash
# 查看当前分支
git branch
# * main    ← 星号表示当前所在分支

# 查看所有分支（包括远程）
git branch -a
```

## 创建分支

```bash
# 创建新分支
git branch feature-login

# 创建并切换到新分支（更常用）
git checkout -b feature-login
# 或者用新语法
git switch -c feature-login
```

命名建议：
- `feature/xxx` — 新功能
- `fix/xxx` — 修复
- `experiment/xxx` — 实验
- `release/xxx` — 发布准备

## 切换分支

```bash
# 切换到已有分支
git checkout main
# 或者
git switch main

# 查看当前分支
git branch
```

切换分支时，Git 会把工作区的文件恢复到目标分支的状态。**确保你的修改已经提交或暂存**，否则切换可能导致修改丢失或冲突。

## 在分支上工作

```bash
# 1. 创建并切换到新分支
git switch -c feature-login

# 2. 在新分支上正常开发、提交
git add login.py
git commit -m "feat: 实现登录页面"

git add auth.py
git commit -m "feat: 添加认证逻辑"

# 3. 查看分支上的提交
git log --oneline

# 4. 切回主分支
git switch main

# 5. 此时工作区回到 main 分支的状态，新功能文件"消失"了
# （实际保存在 feature-login 分支中）
```

## 合并分支

当分支上的开发完成后，把它合并回主线（详见下一节）：

```bash
git switch main
git merge feature-login
```

## 删除分支

```bash
# 删除已合并的分支
git branch -d feature-login

# 强制删除未合并的分支（⚠️ 会丢失该分支的修改）
git branch -D experiment-bad-idea
```

## 常见误区

1. **忘记切换分支**：在 `main` 上直接开发新功能，导致主线上堆满了未完成的代码。养成习惯：新功能一定在新分支上做。
2. **分支太多不清理**：合并后的分支如果不删除，`git branch` 会列出一大堆。定期清理已合并的分支。
3. **分支名太随意**：`test`、`new`、`tmp` 这种名字过几天就忘了是什么。用有描述性的名字。
4. **长时间不合并**：一个分支开发太久（几周），和主线差异越来越大，合并时会非常痛苦。尽量保持短周期合并。
