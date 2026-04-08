# GPU环境与模型检查点

> 本节你将学到：配置 GPU 加速环境的完整流程，以及如何在 PyTorch 中保存与加载包含状态字典的标准模型检查点。

## 核心概念

为了利用硬件进行高效的深度学习训练，首先需要正确配置底层的 GPU 加速环境。在环境搭建完成后，为了防止训练过程中的意外中断导致数据丢失，或者为了后续继续训练和模型部署，必须掌握标准检查点的保存与加载逻辑。

## 详细说明

### GPU加速与CUDA配置流程

要让深度学习模型在 GPU 上运行，需要自底向上进行一系列软硬件环境的配置。完整的配置流程分为四个关键步骤：

1. **NVIDIA驱动**：这是最底层的系统软件，负责让操作系统能够识别并与 NVIDIA 硬件显卡进行通信。
2. **CUDA Toolkit**：NVIDIA 推出的并行计算平台和编程模型。它提供了 GPU 编程所需的编译器（如 `nvcc`）和基础数学库。
3. **cuDNN**：NVIDIA 专门为深度神经网络设计的 GPU 加速库。它在 CUDA 的基础上，提供了高度优化的卷积、池化等常见深度学习操作的底层实现。
4. **PyTorch GPU版本**：最上层的深度学习框架。在安装时必须选择与之相匹配的 CUDA 版本，以便在代码中调用 GPU 资源。

### PyTorch标准检查点机制

在 PyTorch 中，保存模型的最佳实践不是仅仅保存模型的参数，而是保存一个包含训练完整状态的“字典”。

一个完整的检查点通常需要包含以下关键字段：
- `epoch`：当前训练所到达的轮次数，用于记录训练进度。
- `model_state_dict`：模型当前的可学习参数和权重状态字典。
- `optimizer_state_dict`：优化器当前的动量和梯度等状态信息，这对 Adam 等自适应优化器恢复训练至关重要。
- `scheduler_state_dict`：学习率调度器的状态信息，用于准确恢复后续的学习率衰减策略。

## 代码示例

以下代码展示了如何保存与加载包含上述状态字典的标准检查点。

### 保存检查点

在训练过程中（例如每个 epoch 结束后），可以使用 `torch.save()` 将各种状态打包成一个字典并保存到本地文件。

```python
import torch

# 假设以下对象已在训练代码中初始化: model, optimizer, scheduler, epoch

# 保存完整检查点
torch.save({
    'epoch': epoch,
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
    'scheduler_state_dict': scheduler.state_dict(),
}, 'checkpoint.pt')
```

### 加载检查点

在恢复训练或进行推理前，需要从文件中加载字典，并分别将状态重新加载到对应的对象实例中。

```python
import torch

# 1. 加载保存的字典文件 (映射到 CPU 以避免 GPU 内存冲突)
checkpoint = torch.load('checkpoint.pt', map_location='cpu')

# 2. 恢复训练轮次
start_epoch = checkpoint['epoch'] + 1

# 3. 恢复模型权重
model.load_state_dict(checkpoint['model_state_dict'])

# 4. 恢复优化器状态和学习率调度器状态
optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
scheduler.load_state_dict(checkpoint['scheduler_state_dict'])

# 恢复后即可继续训练或直接进行评估
model.train() # 或者 model.eval()
```

## 常见误区

- **只保存模型权重**：如果只保存 `model.state_dict()` 而不包含优化器等字段，当训练意外中断时，虽然模型权重没有丢失，但由于缺乏优化器的动量等状态历史数据，将无法**无缝恢复**训练过程，这会导致损失函数出现突变。
- **环境版本不匹配**：在配置环境时，PyTorch 的 CUDA 版本必须与系统安装的 NVIDIA 驱动和 CUDA Toolkit 版本保持兼容，否则框架无法正确调用 GPU。

## 要点回顾

- 配置 GPU 加速与 CUDA 的完整自底向上流程为：NVIDIA驱动 -> CUDA Toolkit -> cuDNN -> PyTorch GPU版本。
- PyTorch 中保存和加载完整检查点的标准做法是：使用 `torch.save()` 保存一个包含 `epoch`、`model_state_dict`、`optimizer_state_dict` 等关键字段的字典，加载时再分别提取并恢复至对应实例。