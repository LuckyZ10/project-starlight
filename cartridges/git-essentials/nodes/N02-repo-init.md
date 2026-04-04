# 初始化仓库

## 核心概念

使用 Git 的第一步是创建（或获取）一个**仓库**。仓库本质上就是一个包含了 `.git` 目录的文件夹，Git 在这个目录中保存所有的版本历史。

## git init — 从零开始

在空文件夹（或已有项目的文件夹）中初始化一个新仓库：

```bash
# 创建项目文件夹并进入
mkdir my-project
cd my-project

# 初始化 Git 仓库
git init
# 输出：Initialized empty Git repository in /path/to/my-project/.git/
```

执行后，文件夹里会多出一个隐藏的 `.git` 目录。**不要手动修改这个目录的内容！**

```bash
# 查看隐藏目录
ls -la
# drwxr-xr-x  .git
```

## git clone — 获取已有仓库

如果你想参与一个已有的项目（比如从 GitHub 上），用 `clone` 把远程仓库复制到本地：

```bash
# 通过 HTTPS
git clone https://github.com/user/repo.git

# 通过 SSH
git clone git@github.com:user/repo.git

# clone 到指定目录名
git clone https://github.com/user/repo.git my-folder
```

`clone` 会自动创建文件夹、初始化 `.git`、拉取所有历史记录，并自动设置好远程仓库的关联。

## 查看仓库状态

```bash
git status
```

这是最常用的 Git 命令之一，告诉你：
- 当前在哪个分支
- 有哪些文件被修改了
- 哪些修改已暂存、哪些还没暂存
- 有没有未追踪的新文件

```bash
# 示例输出
On branch main
Untracked files:
  (use "git add <file>..." to include in what will be committed)
        hello.py

nothing added to commit but untracked files present (use "git add" to track)
```

## gitignore — 忽略不需要追踪的文件

有些文件不应该放进版本控制（编译产物、密码文件、依赖包等）。创建 `.gitignore` 文件来排除它们：

```bash
# .gitignore
__pycache__/
*.pyc
.env
node_modules/
*.o
dist/
.DS_Store
```

## 常见误区

1. **在 home 目录 git init**：不要在 `~` 或 `/` 这样的大目录初始化 Git，会追踪大量无关文件。应该在具体的项目文件夹中操作。
2. **忽略 `.gitignore` 本身**：`.gitignore` 应该被提交到仓库中，这样团队所有人共享同一套忽略规则。
3. **误删 `.git` 目录**：删掉 `.git` 就等于删掉了所有版本历史，仓库变回普通文件夹。无法恢复。
4. **在仓库内嵌套仓库**：一个 Git 仓库内部不应该有另一个 `.git` 目录（除非用 git submodule）。这会导致 Git 行为异常。
