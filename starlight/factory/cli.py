#!/usr/bin/env python3
"""Cartridge Factory CLI — 从命令行制造 .star 卡带

用法:
    python -m starlight.factory.cli <input.md> --id <cartridge-id> [--output-dir ./cartridges]

示例:
    python -m starlight.factory.cli transformer.md --id transformer-complete
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)


async def run(args):
    from starlight.factory.pipeline import CartridgeFactory
    from starlight.config import settings

    # 构建 LLM 调用函数
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    async def call_llm(messages: list[dict]) -> str:
        system_parts = []
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                chat_messages.append(msg)

        if not chat_messages:
            chat_messages = [{"role": "user", "content": "开始"}]

        system_text = "\n\n".join(system_parts) if system_parts else None

        kwargs = {
            "model": settings.llm_model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system_text:
            kwargs["system"] = system_text

        response = await client.messages.create(**kwargs)
        return response.content[0].text

    # 读取输入
    with open(args.input, encoding="utf-8") as f:
        content = f.read()

    title = args.title or os.path.splitext(os.path.basename(args.input))[0]

    print(f"📖 读取完成：{title} ({len(content)} 字符)")

    # 运行制造流水线
    factory = CartridgeFactory(
        call_llm,
        coverage_threshold=args.coverage,
        max_audit_rounds=args.max_rounds,
    )

    result = await factory.manufacture(
        title=title,
        content=content,
        cartridge_id=args.id,
        output_dir=args.output_dir,
    )

    # 输出结果
    print()
    print(result.summary())
    print()
    print(f"📁 卡带目录：{result.cartridge_dir}")
    print(f"📄 manifest：{result.manifest_path}")

    # 如果有验证问题，打印详情
    if result.validation.issues:
        print()
        print("🔍 验证问题详情：")
        for issue in result.validation.issues:
            icon = {"critical": "🔴", "warning": "🟡", "suggestion": "💡"}.get(issue.severity, "❓")
            print(f"  {icon} [{issue.severity}] {issue.description[:100]}")
            if issue.suggestion:
                print(f"     → {issue.suggestion[:100]}")


def main():
    parser = argparse.ArgumentParser(description="Cartridge Factory CLI")
    parser.add_argument("input", help="输入 Markdown 文件路径")
    parser.add_argument("--id", required=True, help="卡带唯一 ID")
    parser.add_argument("--title", default=None, help="课程标题（默认取文件名）")
    parser.add_argument("--output-dir", default="./cartridges", help="输出目录")
    parser.add_argument("--coverage", type=float, default=99.0, help="覆盖率阈值 (%%)")
    parser.add_argument("--max-rounds", type=int, default=3, help="最大审计轮数")
    parser.add_argument("--verbose", action="store_true", help="详细日志")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
