# 控制流

## 核心概念

程序默认从上到下一行一行执行。**控制流**让你改变这个顺序——根据条件选择执行不同的代码，或者重复执行某段代码。

## if / elif / else

根据条件决定执行哪个分支：

```python
score = 85

if score >= 90:
    print("优秀")
elif score >= 80:
    print("良好")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

要点：
- `if` 后面跟条件，以冒号 `:` 结尾
- 每个分支的代码要**缩进**（4 个空格）
- `elif` 是 "else if" 的缩写，可以有多个
- `else` 是兜底分支，不需要条件

## 比较运算符

| 运算符 | 含义 |
|--------|------|
| `==` | 等于 |
| `!=` | 不等于 |
| `>` | 大于 |
| `<` | 小于 |
| `>=` | 大于等于 |
| `<=` | 小于等于 |

## 逻辑运算符

```python
age = 25
has_ticket = True

if age >= 18 and has_ticket:
    print("可以入场")

if age < 12 or age > 65:
    print("享受优惠票价")

if not has_ticket:
    print("请先购票")
```

## for 循环

遍历一个序列（列表、字符串、范围等）：

```python
# 遍历列表
fruits = ["苹果", "香蕉", "橙子"]
for fruit in fruits:
    print(f"我喜欢{fruit}")

# 使用 range
for i in range(5):       # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 10, 2):  # 1, 3, 5, 7, 9
    print(i)
```

## while 循环

只要条件为真，就一直执行：

```python
count = 0
while count < 5:
    print(f"第 {count} 次")
    count += 1
```

⚠️ 注意：一定要有让条件变为 False 的机制，否则会无限循环！

## break 和 continue

```python
# break：提前退出整个循环
for num in range(10):
    if num == 5:
        break
    print(num)    # 输出 0, 1, 2, 3, 4

# continue：跳过当前这一轮，继续下一轮
for num in range(5):
    if num == 2:
        continue
    print(num)    # 输出 0, 1, 3, 4
```

## 常见误区

1. **忘记冒号**：`if`、`for`、`while` 后面都要加 `:`。
2. **缩进不一致**：同一代码块必须用相同的缩进。
3. **while 死循环**：忘记更新循环变量。
4. **用 `=` 代替 `==`**：在条件判断中要用 `==` 比较相等。
