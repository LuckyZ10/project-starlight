```markdown
# Softmax与交叉熵

> 本节你将学到：Softmax函数和交叉熵损失在概率分布和分类任务中的作用。

## 核心概念
### Softmax函数
Softmax函数是神经网络输出层的标准组件，其功能是将任意实数向量转换为合法的概率分布。这意味着，输出向量中的所有值都是非负的，且它们的总和为1。

### 交叉熵损失
交叉熵损失（Cross-Entropy Loss）是分类任务的标准优化目标，源于信息论的熵概念。它衡量的是实际概率分布与预测概率分布之间的差异。

## 详细说明
### Softmax函数的详细说明
Softmax函数对每个输入值进行指数运算，然后对这些指数值进行归一化处理。公式如下：

$$
\text{Softmax}(x_i) = \frac{e^{x_i}}{\sum_{j=1}^{n} e^{x_j}}
$$

其中，\( x_i \) 是输入向量的第 \( i \) 个元素，\( n \) 是输入向量的长度。

### 交叉熵损失的详细说明
交叉熵损失用于衡量两个概率分布之间的差异。其公式如下：

$$
L(\theta) = -\sum_{i=1}^{n} y_i \log(\hat{y}_i)
$$

其中，\( y_i \) 是真实标签，\( \hat{y}_i \) 是模型预测的概率。

## 代码示例
```python
import numpy as np

def softmax(x):
    """Softmax函数实现"""
    exp_x = np.exp(x - np.max(x))
    return exp_x / np.sum(exp_x, axis=0)

def cross_entropy_loss(y_true, y_pred):
    """交叉熵损失函数实现"""
    return -np.sum(y_true * np.log(y_pred))
```

## 常见误区
- 错误地认为Softmax函数的输出总是最大的那个元素的概率最大。
- 将交叉熵损失应用于回归任务。

## 要点回顾
- Softmax函数将任意实数向量转换为合法的概率分布。
- 交叉熵损失是分类任务的标准优化目标，衡量实际概率分布与预测概率分布之间的差异。
```