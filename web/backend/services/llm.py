"""LLM streaming service using Anthropic-compatible API."""
from __future__ import annotations

import os

from anthropic import Anthropic

API_KEY = os.environ.get(
    "STARLIGHT_LLM_API_KEY",
    "303aa793ae3f48ac84d49d1270c04868.svybnJieCdyx23ZU",
)
BASE_URL = os.environ.get("STARLIGHT_LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
MODEL = os.environ.get("STARLIGHT_LLM_MODEL", "glm-5.1")


async def stream_chat(messages: list[dict], max_tokens: int = 8192):
    """Stream chat responses from LLM."""
    client = Anthropic(api_key=API_KEY, base_url=BASE_URL)

    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
