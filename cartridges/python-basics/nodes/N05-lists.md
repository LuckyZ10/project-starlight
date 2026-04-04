# 列表

## 核心概念

列表（list）是 Python 中最常用的数据结构，用来存储**有序的**元素集合。列表可以包含任何类型的元素，甚至混合类型。

```python
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", True, 3.14]
empty = []
```

## 索引与切片

列表的每个元素都有一个**位置编号（索引）**，从 0 开始。负数索引从末尾倒数。

```python
colors = ["红", "橙", "黄", "绿", "蓝"]

print(colors[0])     # 红（第一个）
print(colors[-1])    # 蓝（最后一个）
print(colors[1:3])   # ["橙", "黄"]（切片：左闭右开）
print(colors[:2])    # ["红", "橙"]（从头到索引 2）
print(colors[2:])    # ["黄", "绿", "蓝"]（从索引 2 到末尾）
```

## 常用操作

```python
fruits = ["苹果", "香蕉"]

# 添加元素
fruits.append("橙子")          # 末尾添加
fruits.insert(1, "葡萄")       # 在索引 1 处插入

# 删除元素
fruits.remove("香蕉")          # 按值删除（只删第一个）
last = fruits.pop()             # 删除并返回最后一个
del fruits[0]                   # 按索引删除

# 查找
fruits = ["苹果", "香蕉", "苹果"]
print(fruits.count("苹果"))     # 2
print(fruits.index("香蕉"))     # 1

# 排序
numbers = [3, 1, 4, 1, 5, 9]
numbers.sort()                  # 原地排序 → [1, 1, 3, 4, 5, 9]
sorted_nums = sorted(numbers, reverse=True)   # 返回新列表，降序

# 长度
print(len(fruits))              # 3
```

## 列表推导式

Python 有一种简洁的方式来创建新列表：

```python
# 传统写法
squares = []
for x in range(10):
    squares.append(x ** 2)

# 列表推导式（更 Pythonic）
squares = [x ** 2 for x in range(10)]

# 带条件
evens = [x for x in range(20) if x % 2 == 0]
```

## 列表是可变的

```python
a = [1, 2, 3]
b = a          # b 和 a 指向同一个列表！
b[0] = 99
print(a)       # [99, 2, 3] — a 也变了！

# 如果要复制
c = a.copy()   # 或 c = list(a) 或 c = a[:]
```

## 常见误区

1. **索引越界**：列表有 3 个元素，访问 `lst[3]` 会报 IndexError。有效索引是 0~2。
2. **遍历时修改列表**：在 `for` 循环中删除元素会导致跳过元素。用列表推导式创建新列表或倒序遍历。
3. **用 `==` 比较含义搞混**：`[1, 2] == [1, 2]` 是 True（值相等），但 `a is b` 可能是 False（不同对象）。
4. **`sort()` vs `sorted()`**：`sort()` 原地修改，返回 None；`sorted()` 返回新列表。不要写 `x = x.sort()`。
