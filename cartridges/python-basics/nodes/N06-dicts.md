# 字典

## 核心概念

字典（dict）是**键值对**的集合。每个键（key）唯一地映射到一个值（value）。你可以把它想象成一本真正的字典——通过"词条"（键）快速查找"释义"（值）。

```python
student = {
    "name": "小明",
    "age": 18,
    "scores": [90, 85, 92]
}
```

字典的查找速度极快，不管存了多少条数据，查找时间几乎一样。

## 基本操作

```python
# 创建
person = {"name": "Alice", "age": 25}

# 访问值
print(person["name"])           # Alice
print(person.get("email", "无"))  # 无（键不存在时返回默认值，不报错）

# 添加/修改
person["email"] = "alice@example.com"   # 新增
person["age"] = 26                       # 修改已有键

# 删除
del person["email"]
age = person.pop("age")        # 删除并返回值

# 检查键是否存在
if "name" in person:
    print("有 name 字段")
```

## 遍历字典

```python
scores = {"数学": 95, "英语": 88, "物理": 92}

# 遍历键
for subject in scores:
    print(subject)

# 遍历键值对
for subject, score in scores.items():
    print(f"{subject}: {score} 分")

# 遍历值
for score in scores.values():
    print(score)

# 遍历键（显式）
for subject in scores.keys():
    print(subject)
```

## 字典推导式

和列表推导式类似，可以简洁地创建字典：

```python
# 把列表转成 {元素: 出现次数} 的字典
words = ["apple", "banana", "apple", "cherry", "banana"]
word_count = {word: words.count(word) for word in set(words)}
# {'apple': 2, 'banana': 2, 'cherry': 1}

# 键值互换
original = {"a": 1, "b": 2, "c": 3}
swapped = {v: k for k, v in original.items()}
# {1: 'a', 2: 'b', 3: 'c'}
```

## 嵌套字典

字典的值可以是任何类型，包括另一个字典：

```python
students = {
    "001": {"name": "小明", "age": 18},
    "002": {"name": "小红", "age": 17},
}
print(students["001"]["name"])   # 小明
```

## 常见误区

1. **键不存在直接访问**：`person["phone"]` 如果 "phone" 不在字典中会抛出 KeyError。用 `person.get("phone")` 更安全。
2. **键必须是不可变类型**：字符串、数字、元组可以当键；列表和字典不行（它们是可变的，不能哈希）。
3. **遍历时修改字典**：在 `for key in d:` 循环中 `del d[key]` 会报 RuntimeError。应该先收集要删除的键，循环后再删。
4. **字典无序？**：Python 3.7+ 保证字典按插入顺序排列。但你不应该依赖顺序来做逻辑判断。
