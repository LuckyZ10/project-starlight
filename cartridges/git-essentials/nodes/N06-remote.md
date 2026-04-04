# 远程仓库

## 核心概念

远程仓库是托管在网络上的 Git 仓库副本（如 GitHub、GitLab、Gitee）。它让你的代码可以**跨设备同步**、**多人协作**，同时起到备份作用。

## 远程仓库的协作模型

```
你的电脑 (本地仓库)  ←→  GitHub (远程仓库)  ←→  同事的电脑 (本地仓库)
     push/pull                push/pull
```

每个人都有完整的本地仓库，通过 push/pull 与远程同步。

## 常用远程操作

### git clone — 克隆远程仓库

```bash
# HTTPS 方式（简单，推荐新手）
git clone https://github.com/user/repo.git

# SSH 方式（需要配置 SSH Key，更方便）
git clone git@github.com:user/repo.git

# 克隆到指定目录
git clone https://github.com/user/repo.git my-project
```

### git remote — 管理远程仓库

```bash
# 查看远程仓库
git remote
# origin

# 查看详细信息
git remote -v
# origin  https://github.com/user/repo.git (fetch)
# origin  https://github.com/user/repo.git (push)

# 添加远程仓库（如果你是本地 init 后才想关联远程）
git remote add origin https://github.com/user/repo.git

# 修改远程仓库地址
git remote set-url origin https://github.com/user/new-repo.git
```

### git push — 推送到远程

```bash
# 第一次推送，设置上游分支
git push -u origin main
# -u（或 --set-upstream）把本地 main 和远程 origin/main 关联起来

# 之后直接推送
git push

# 推送其他分支
git push origin feature-login

# 删除远程分支
git push origin --delete feature-login
```

### git pull — 拉取远程更新

```bash
# 拉取并合并当前分支的远程更新
git pull
# 等价于 git fetch + git merge

# 拉取时使用 rebase（保持线性历史）
git pull --rebase
```

### git fetch — 只获取不合并

```bash
# 下载远程更新但不自动合并
git fetch origin

# 查看远程有什么新提交
git log origin/main --oneline -5

# 手动合并
git merge origin/main
```

`fetch` 比 `pull` 更安全——先看看远程有什么变化，再决定怎么合并。

## 协作工作流

典型的 Git 协作流程：

```bash
# 1. 克隆项目
git clone https://github.com/team/project.git
cd project

# 2. 创建功能分支
git switch -c feature/add-search

# 3. 开发 + 提交
git add .
git commit -m "feat: 添加搜索功能"

# 4. 推送分支到远程
git push -u origin feature/add-search

# 5. 在 GitHub 上创建 Pull Request（浏览器操作）

# 6. Code Review 后合并到 main

# 7. 同步本地 main
git switch main
git pull
```

## 常见误区

1. **push 被拒绝**：远程有别人推送的新提交，你直接 push 会失败。先 `git pull` 合并远程更新，再 `git push`。
2. **不确定 pull 会不会冲突**：用 `git fetch` 先看看远程的变化，再决定是否 merge。
3. **在 main 上直接 push**：团队项目中，main 应该通过 Pull Request 合并，不要直接 push。
4. **忘记设置上游分支**：第一次 push 新分支时需要 `-u origin branch-name`，否则后续 `git push` 不知推到哪里。
5. **凭据管理**：HTTPS 方式每次 push 都要输密码很烦。配置凭据缓存：`git config --global credential.helper store`（或用 SSH Key）。
