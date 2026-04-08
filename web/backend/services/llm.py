"""LLM streaming service using Anthropic-compatible API."""
from __future__ import annotations

import asyncio
import os

from anthropic import Anthropic

API_KEY = os.environ.get(
    "STARLIGHT_LLM_API_KEY",
    "303aa793ae3f48ac84d49d1270c04868.svybnJieCdyx23ZU",
)
BASE_URL = os.environ.get("STARLIGHT_LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
MODEL = os.environ.get("STARLIGHT_LLM_MODEL", "glm-5.1")


def _extract_system(messages: list[dict]) -> tuple[str, list[dict]]:
    """Separate system message from user/assistant messages."""
    system = ""
    chat_msgs = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            chat_msgs.append(m)
    if not chat_msgs:
        chat_msgs = [{"role": "user", "content": "Hello"}]
    return system, chat_msgs


async def stream_chat(messages: list[dict], max_tokens: int = 8192):
    """Stream chat responses from LLM (non-blocking)."""
    system, chat_msgs = _extract_system(messages)
    client = Anthropic(api_key=API_KEY, base_url=BASE_URL)

    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system if system else "You are a helpful tutor.",
        messages=chat_msgs,
    ) as stream:
        for text in stream.text_stream:
            # Yield control to event loop so SSE isn't blocked
            await asyncio.sleep(0)
            yield text
