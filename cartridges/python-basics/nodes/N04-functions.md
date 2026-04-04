# 函数

## 核心概念

函数是**可复用的代码块**。你把一段逻辑"包装"起来，给它起个名字，之后通过名字就能调用它，不用重复写同样的代码。

```python
def greet(name):
    return f"你好，{name}！"

message = greet("小明")
print(message)   # 你好，小明！
```

`def` 是 define（定义）的缩写，后面跟函数名和参数列表，以冒号 `:` 结尾。函数体需要缩进。

## 参数

函数可以接收零个或多个参数：

```python
# 无参数
def say_hello():
    print("Hello!")

# 多个参数
def add(a, b):
    return a + b

# 默认参数
def power(base, exp=2):
    return base ** exp

print(power(3))      # 9（exp 默认为 2）
print(power(3, 3))   # 27（覆盖默认值）
```

## 返回值

`return` 语句把结果"交还"给调用者。**没有 return 的函数默认返回 `None`。**

```python
def check_even(n):
    if n % 2 == 0:
        return True
    return False

result = check_even(4)   # True
```

函数也可以返回多个值（本质是返回一个元组）：

```python
def min_max(numbers):
    return min(numbers), max(numbers)

lo, hi = min_max([3, 1, 4, 1, 5, 9])
```

## 作用域

函数内部定义的变量是**局部变量**，函数外访问不到：

```python
def compute():
    result = 42    # 局部变量

compute()
# print(result)   # ❌ NameError!
```

## 常见误区

1. **忘记调用**：写了 `def greet(name): ...` 但从没写过 `greet("小明")`，函数不会自动执行。
2. **可变默认参数**：`def append_to(item, lst=[])` 中的 `[]` 只在函数定义时创建一次，多次调用会共享同一个列表。正确做法是 `lst=None`，然后在函数内 `if lst is None: lst = []`。
3. **混用 return 和 print**：`return` 把值交给调用者；`print` 只是在屏幕上显示。在函数里用 `print` 代替 `return` 会导致调用者拿到 `None`。
4. **return 放错位置**：把 `return` 写在循环里面，导致循环只执行一次就返回了。注意缩进层级。
