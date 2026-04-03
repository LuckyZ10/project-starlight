# 数据类型

## 核心概念

Python 中每个值都有一个"类型"，决定了它能做什么操作。最基础的四种类型：

## 字符串 (str)

字符串就是文本，用单引号或双引号包裹：

```python
greeting = "你好"
name = 'Starlight'
message = greeting + "，" + name    # 字符串拼接
length = len(message)               # 获取长度
```

常用操作：`+` 拼接、`*` 重复、`len()` 取长度、`[索引]` 取字符。

## 整数 (int)

整数就是没有小数点的数字：

```python
count = 42
negative = -7
big = 1_000_000    # 可以用下划线分隔，等于 1000000
result = 10 // 3   # 整数除法，结果是 3
```

## 浮点数 (float)

带小数点的数字：

```python
pi = 3.14159
temperature = -0.5
result = 10 / 3    # 普通除法，结果是 3.3333...
```

⚠️ 浮点数有精度问题：`0.1 + 0.2` 不等于 `0.3`，而是 `0.30000000000000004`。

## 列表 (list)

列表是一个有序集合，可以放任意类型的元素：

```python
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True]    # 可以混合类型

# 常用操作
fruits.append("葡萄")       # 添加元素
first = fruits[0]           # 索引访问（从 0 开始）
fruits[1] = "西瓜"          # 修改元素
count = len(fruits)         # 获取长度
```

## 类型转换

```python
age_str = "25"
age = int(age_str)          # 字符串 → 整数
price = float("9.99")       # 字符串 → 浮点数
text = str(42)              # 整数 → 字符串
```

## type() 函数

用 `type()` 查看任何值的类型：

```python
print(type("hello"))    # <class 'str'>
print(type(42))         # <class 'int'>
print(type(3.14))       # <class 'float'>
print(type([1, 2]))     # <class 'list'>
```
