# 合并

## 核心概念

分支开发完成后，需要把它**合并**回主线（或其他目标分支）。Git 提供了两种合并方式：`merge` 和 `rebase`。这一节重点讲 `merge`。

## git merge — 基本合并

```bash
# 1. 切到目标分支（通常是 main）
git switch main

# 2. 合并指定分支
git merge feature-login

# 3. 删除已合并的分支（可选）
git branch -d feature-login
```

合并有三种情况：

### 情况 1：快进合并（Fast-forward）

如果 main 分支没有新的提交，Git 直接把 main 指针移到 feature 分支的最新提交：

```
合并前：main → A → B → C
                     ↑ feature-login

合并后：main → A → B → C
                     ↑ main, feature-login
```

没有分叉，历史是一条直线。

### 情况 2：三方合并

如果 main 和 feature 各自有新的提交，Git 会创建一个新的**合并提交**：

```
合并前：
    main:    A → B → D → E
                     ↗
    feature: A → B → C

合并后：
    main:    A → B → D → E → M（合并提交）
                     ↗       ↗
                C ──────────┘
```

### 情况 3：合并冲突

如果两个分支修改了**同一个文件的同一行**，Git 无法自动决定保留哪个版本，就需要你手动解决冲突。

## 处理冲突

```bash
git merge feature-login
# 输出：CONFLICT (content): Merge conflict in login.py
```

打开冲突文件，你会看到类似这样的标记：

```python
# 文件 login.py
def get_username():
<<<<<<< HEAD
    return input("请输入用户名: ")     # ← 当前分支（main）的版本
=======
    return input("Username: ")         # ← feature 分支的版本
>>>>>>> feature-login
```

解决步骤：

```bash
# 1. 手动编辑文件，选择保留的版本（删除不需要的和标记符号）
def get_username():
    return input("请输入用户名: ")     # 保留 main 的版本

# 2. 标记冲突已解决
git add login.py

# 3. 完成合并
git commit
#（Git 会自动生成合并提交信息）
```

## 取消合并

如果合并出错，可以在提交前取消：

```bash
git merge --abort    # 放弃合并，恢复到合并前的状态
```

## 查看合并状态

```bash
# 查看哪些分支已合并到当前分支
git branch --merged

# 查看哪些分支还没合并
git branch --no-merged
```

## 常见误区

1. **冲突是坏事**：冲突不是错误，而是 Git 诚实地说"这两处修改有矛盾，你来决定"。项目越活跃，冲突越正常。
2. **忽略冲突直接 commit**：看到 `<<<<<<<` 标记就直接提交，会把标记符号留在代码里。务必确认文件内容正确后再 `git add`。
3. **大量冲突时慌了**：如果冲突太多，用 `git merge --abort` 取消，先在 feature 分支上 `git rebase main`（变基到最新 main），减少冲突量。
4. **总是用 `-X theirs`**：`git merge -X theirs feature` 强制采用对方版本，可能丢失自己的修改。只在确认安全时使用。
