# 字符串操作

## 核心概念

字符串是 Python 中表示文本的数据类型，用单引号或双引号创建。字符串是**不可变的**——创建后不能修改，所有"修改"操作都返回新字符串。

```python
s1 = 'Hello'
s2 = "World"
s3 = """这是一个
多行字符串"""
```

## 字符串格式化

Python 有多种把变量嵌入字符串的方式：

```python
name = "小明"
age = 18

# f-string（推荐，Python 3.6+）
print(f"我叫{name}，今年{age}岁")
print(f"明年{age + 1}岁")              # 可以放表达式

# format() 方法
print("我叫{}，今年{}岁".format(name, age))

# 旧式 % 格式化（了解即可）
print("我叫%s，今年%d岁" % (name, age))
```

f-string 还支持格式控制：

```python
pi = 3.14159265
print(f"{pi:.2f}")        # 3.14（保留两位小数）
print(f"{42:05d}")        # 00042（5位数，前面补零）
print(f"{'hi':>10}")      # "        hi"（右对齐，宽度 10）
```

## 常用方法

```python
s = "Hello, World!"

# 大小写
s.lower()          # "hello, world!"
s.upper()          # "HELLO, WORLD!"
s.title()          # "Hello, World!"
s.capitalize()     # "Hello, world!"

# 查找与判断
s.find("World")    # 7（返回索引，找不到返回 -1）
s.count("l")       # 3
"hello".startswith("he")   # True
"test.py".endswith(".py")  # True

# 分割与合并
"a,b,c".split(",")              # ["a", "b", "c"]
"one  two  three".split()       # ["one", "two", "three"]（按空白分割）
", ".join(["苹果", "香蕉", "橙子"])  # "苹果, 香蕉, 橙子"

# 去除空白
"  hello  ".strip()     # "hello"
"  hello  ".lstrip()    # "hello  "
"  hello  ".rstrip()    # "  hello"

# 替换
"hello world".replace("world", "Python")   # "hello Python"
```

## 切片

字符串切片和列表切片规则一样：

```python
s = "Hello, World!"
print(s[0:5])     # "Hello"
print(s[7:])      # "World!"
print(s[-6:])     # "orld!"
print(s[::2])     # "Hlo ol!"（每隔一个字符取一个）
print(s[::-1])    # "!dlroW ,olleH"（反转）
```

## 常见误区

1. **字符串不可变**：`s[0] = "h"` 会报 TypeError。要用 `s = "h" + s[1:]` 或 `s.replace()` 来"修改"。
2. **`==` vs `is`**：比较字符串内容用 `==`，`is` 比较的是对象身份（是否是同一个对象）。
3. **拼接大量字符串**：用 `+` 在循环中拼接字符串效率低（每次都创建新字符串）。用 `"".join(list_of_strings)` 更高效。
4. **忘记 encode/decode**：读写文件或网络传输时，字符串需要编码为字节：`s.encode("utf-8")`，反过来是 `b.decode("utf-8")`。
