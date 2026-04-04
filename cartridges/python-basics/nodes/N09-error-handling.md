# 异常处理

## 核心概念

程序运行时难免出错——文件找不到、网络断开、用户输入了非法数据。**异常处理**让你的程序遇到错误时不直接崩溃，而是优雅地处理问题。

```python
# 没有异常处理
result = 10 / 0    # ❌ ZeroDivisionError，程序崩溃！

# 有异常处理
try:
    result = 10 / 0
except ZeroDivisionError:
    print("除数不能为零！")     # 程序继续运行
```

## try / except / else / finally

完整的异常处理结构：

```python
try:
    number = int(input("请输入一个数字："))
    result = 100 / number
except ValueError:
    print("输入的不是有效数字！")
except ZeroDivisionError:
    print("不能除以零！")
except Exception as e:
    print(f"未知错误：{e}")
else:
    # try 块没有异常时执行
    print(f"结果是 {result}")
finally:
    # 无论如何都执行（常用于清理资源）
    print("计算结束")
```

执行顺序：
1. `try` 块中的代码正常执行
2. 如果发生异常，跳到对应的 `except` 块
3. 如果没有异常，执行 `else` 块
4. 无论是否有异常，`finally` 块都会执行

## 捕获多个异常

```python
try:
    value = int("abc")
except (ValueError, TypeError) as e:
    print(f"类型错误：{e}")
```

## 常见异常类型

| 异常 | 说明 |
|------|------|
| `ValueError` | 值不合法，如 `int("abc")` |
| `TypeError` | 类型错误，如 `"2" + 2` |
| `KeyError` | 字典键不存在 |
| `IndexError` | 索引越界 |
| `FileNotFoundError` | 文件不存在 |
| `ZeroDivisionError` | 除以零 |
| `NameError` | 变量未定义 |
| `AttributeError` | 对象没有该属性/方法 |

## 抛出异常

用 `raise` 主动抛出异常：

```python
def set_age(age):
    if age < 0:
        raise ValueError("年龄不能为负数")
    if age > 150:
        raise ValueError("年龄不合理")
    return age

try:
    set_age(-5)
except ValueError as e:
    print(e)   # 年龄不能为负数
```

## 自定义异常

```python
class InsufficientFundsError(Exception):
    """余额不足异常"""
    def __init__(self, balance, amount):
        self.balance = balance
        self.amount = amount
        super().__init__(f"余额 {balance} 不足，需要 {amount}")

def withdraw(balance, amount):
    if amount > balance:
        raise InsufficientFundsError(balance, amount)
    return balance - amount
```

## 常见误区

1. **裸 except**：`except:` 会捕获所有异常（包括 KeyboardInterrupt、SystemExit），应该至少用 `except Exception:`。
2. **异常太宽泛**：`except Exception:` 捕获一切异常会掩盖真正的 bug。尽量捕获具体的异常类型。
3. **finally 中的 return**：`finally` 块中的 `return` 会覆盖 `try` 或 `except` 中的返回值，行为反直觉，应避免。
4. **忽略异常**：`except: pass` 什么都不做就吞掉异常，出了问题很难排查。至少记个日志。
