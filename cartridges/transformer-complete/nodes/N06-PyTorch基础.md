```markdown
# PyTorch基础

> 本节你将学到：PyTorch的核心概念，包括Tensor、autograd和nn.Module。

## 核心概念

- **Tensor**：在PyTorch中，Tensor是一个多维数组，它支持GPU加速，这对于深度学习中的大量计算至关重要。Tensor具有几个关键属性：dtype（数据类型）、device（设备，如CPU或GPU）和requires_grad（是否需要计算梯度）。

- **autograd**：autograd是PyTorch中自动微分的基础。它允许用户通过自动微分引擎自动计算函数的梯度。当对Tensor进行操作时，autograd会跟踪这些操作，并允许在需要时进行反向传播。

- **nn.Module**：nn.Module是PyTorch中所有神经网络层的基类。通过继承nn.Module，可以定义自己的神经网络层。`__init__`方法用于声明层中的参数，而`forward`方法定义了前向传播的计算过程。

## 详细说明

- **Tensor**：例如，创建一个4维Tensor的代码如下：

  ```python
  import torch
  tensor = torch.tensor([1, 2, 3, 4], dtype=torch.float32)
  print(tensor)
  ```

  输出：tensor([1., 2., 3., 4.])

- **autograd**：以下是一个使用autograd计算梯度的简单例子：

  ```python
  import torch
  x = torch.tensor([2.0], requires_grad=True)
  y = x**2
  y.backward(torch.tensor([1.0]))  # 计算梯度
  print(x.grad)  # 输出梯度
  ```

  输出：tensor([4.])

- **nn.Module**：以下是如何定义一个简单的神经网络层的例子：

  ```python
  import torch.nn as nn

  class SimpleLayer(nn.Module):
      def __init__(self):
          super(SimpleLayer, self).__init__()
          self.linear = nn.Linear(10, 5)

      def forward(self, x):
          return self.linear(x)
  ```

## 常见误区

- 误以为Tensor和numpy的ndarray完全相同，实际上Tensor具有GPU加速和自动微分等特性。
- 忽略了autograd在深度学习中的重要性，导致无法正确计算梯度。
- 不了解nn.Module的用法，导致无法正确定义和训练神经网络。

## 要点回顾
- PyTorch使用Tensor进行多维数组操作，支持GPU加速。
- autograd提供自动微分功能，允许计算梯度。
- nn.Module是神经网络层的基类，用于定义和训练模型。