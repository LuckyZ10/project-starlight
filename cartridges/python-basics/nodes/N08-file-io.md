# 文件读写

## 核心概念

程序运行时的数据存在内存中，关机就消失了。**文件操作**让你把数据持久化到磁盘上。Python 用内置的 `open()` 函数来操作文件。

## 基本读写

```python
# 写文件
f = open("hello.txt", "w", encoding="utf-8")
f.write("Hello, World!\n")
f.write("你好，世界！\n")
f.close()            # 别忘了关闭！

# 读文件
f = open("hello.txt", "r", encoding="utf-8")
content = f.read()   # 读取全部内容（一个字符串）
print(content)
f.close()
```

## with 语句（推荐）

手动 `open()` + `close()` 容易忘记关文件，或者遇到异常时来不及关。`with` 语句会自动帮你关闭文件：

```python
# 写
with open("data.txt", "w", encoding="utf-8") as f:
    f.write("自动关闭，不用手动 f.close()\n")

# 读
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()
    print(content)
```

即使 `with` 块中发生异常，文件也会被正确关闭。

## 逐行读取

对于大文件，一次性 `read()` 可能占用大量内存。用逐行读取更安全：

```python
# 方法 1：for 循环（推荐）
with open("data.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())   # strip() 去掉末尾的换行符

# 方法 2：readlines()（一次读所有行到列表）
with open("data.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()     # ["第一行\n", "第二行\n", ...]
```

## 文件模式

| 模式 | 说明 |
|------|------|
| `"r"` | 读取（默认），文件不存在则报错 |
| `"w"` | 写入，文件存在则**清空**，不存在则创建 |
| `"a"` | 追加，在文件末尾添加内容 |
| `"x"` | 创建新文件写入，文件已存在则报错 |
| `"rb"` / `"wb"` | 二进制模式读写 |

## 编码问题

文本文件有不同的编码格式（UTF-8、GBK 等）。**始终显式指定 `encoding="utf-8"`**，避免不同系统默认编码不同导致乱码：

```python
# ✅ 推荐
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()

# ❌ 不推荐（依赖系统默认编码）
with open("file.txt", "r") as f:
    content = f.read()
```

## 写入 JSON

JSON 是一种常用的数据交换格式：

```python
import json

data = {"name": "小明", "scores": [90, 85, 92]}

# 写
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 读
with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
```

## 常见误区

1. **忘记 close()**：不用 `with` 时容易忘，导致文件被锁定或数据丢失。
2. **用 `"w"` 模式误删内容**：`"w"` 会清空已有文件！想追加用 `"a"`。
3. **编码不指定**：在 Windows 上默认是 GBK，Linux 上是 UTF-8，不指定可能出乱码。
4. **read() 后再 read()**：文件指针移到末尾了，第二次 `f.read()` 返回空字符串。可以用 `f.seek(0)` 回到开头。
