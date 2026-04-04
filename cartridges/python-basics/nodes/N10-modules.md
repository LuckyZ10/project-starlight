# 模块与包

## 核心概念

当你写的代码越来越多，把所有东西放在一个文件里会变得难以管理。**模块（module）**就是将代码按功能拆分到不同 `.py` 文件中，**包（package）**则是模块的集合——一个包含 `__init__.py` 的文件夹。

```python
# 导入标准库模块
import math
print(math.sqrt(16))      # 4.0
print(math.pi)            # 3.141592653589793

# 导入特定功能
from math import ceil, floor
print(ceil(3.2))          # 4
print(floor(3.8))         # 3

# 起别名
import datetime as dt
now = dt.datetime.now()
print(now.strftime("%Y-%m-%d"))

from collections import Counter
words = ["apple", "banana", "apple"]
c = Counter(words)
print(c)                  # Counter({'apple': 2, 'banana': 1})
```

## 创建自己的模块

任何 `.py` 文件都是一个模块。假设你有 `utils.py`：

```python
# utils.py
def greet(name):
    return f"Hello, {name}!"

PI = 3.14159
```

然后在另一个文件中导入：

```python
# main.py
from utils import greet, PI

print(greet("World"))    # Hello, World!
print(PI)                # 3.14159
```

## 创建包

包就是一个文件夹加上 `__init__.py` 文件：

```
mypackage/
├── __init__.py        # 可以是空文件，也可以定义包级别的导出
├── math_tools.py
└── string_tools.py
```

```python
# 使用包中的模块
from mypackage import math_tools
from mypackage.string_tools import capitalize_words
```

## `__name__` 和 `__main__`

一个常用模式是让模块既能被导入，也能直接运行：

```python
# calculator.py
def add(a, b):
    return a + b

if __name__ == "__main__":
    # 只有直接运行 python calculator.py 时才执行
    print(add(3, 5))    # 8
    # 被其他文件 import 时，这部分不会执行
```

## 常用标准库速查

| 模块 | 用途 |
|------|------|
| `os` | 操作系统接口（路径、环境变量） |
| `sys` | 系统相关（命令行参数、退出） |
| `json` | JSON 编解码 |
| `re` | 正则表达式 |
| `datetime` | 日期和时间 |
| `pathlib` | 面向对象的路径操作 |
| `collections` | 特殊容器（Counter、defaultdict 等） |
| `random` | 随机数生成 |
| `logging` | 日志记录 |

## 常见误区

1. **循环导入**：`a.py` 导入 `b.py`，`b.py` 又导入 `a.py`，导致 ImportError。解决方案：重构代码消除循环依赖，或将导入移到函数内部。
2. **`from module import *`**：把模块的所有内容倒入当前命名空间，容易命名冲突，且不清楚导入了什么。不推荐使用。
3. **文件名和标准库冲突**：把文件命名为 `math.py`、`random.py` 等，会导致 `import math` 导入你自己的文件而非标准库。
4. **忘记 `__init__.py`**：Python 3.3+ 支持"命名空间包"不需要 `__init__.py`，但传统包仍需要。建议每个包目录都放一个空的 `__init__.py`。
