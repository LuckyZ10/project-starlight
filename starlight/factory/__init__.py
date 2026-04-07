# starlight/factory/__init__.py
"""Cartridge Factory — 将原始学习资料转换为 .star 卡带

5 阶段流水线：
  1. EXTRACT  — 知识点原子提取
  2. BUILD    — 分组 + DAG + 难度标定
  3. AUDIT    — 覆盖率审计（≤99% 自动补洞）
  4. VALIDATE — 多视角交叉验证
  5. PACKAGE  — 输出 .star 卡带
"""
from starlight.factory.pipeline import CartridgeFactory

__all__ = ["CartridgeFactory"]
