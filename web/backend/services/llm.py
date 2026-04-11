"""LLM streaming service using Anthropic-compatible API (async)."""
from __future__ import annotations

import os
from anthropic import AsyncAnthropic

API_KEY = os.environ.get(
    "STARLIGHT_LLM_API_KEY",
    "303aa793ae3f48ac84d49d1270c04868.svybnJieCdyx23ZU",
)
BASE_URL = os.environ.get("STARLIGHT_LLM_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
MODEL = os.environ.get("STARLIGHT_LLM_MODEL", "glm-5.1")

# Reuse a single async client
_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=API_KEY, base_url=BASE_URL)
    return _client


def _extract_system(messages: list[dict]) -> tuple[str, list[dict]]:
    """Separate system messages from user/assistant messages."""
    system_parts = []
    chat_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            chat_msgs.append(m)
    if not chat_msgs:
        chat_msgs = [{"role": "user", "content": "Hello"}]
    return "\n\n".join(system_parts), chat_msgs


async def stream_chat(messages: list[dict], max_tokens: int = 4096):
    """Stream chat responses from LLM using true async."""
    system, chat_msgs = _extract_system(messages)
    client = _get_client()

    async with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system if system else "You are a helpful tutor.",
        messages=chat_msgs,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def call_llm(messages: list[dict], max_tokens: int = 2048) -> str:
    """Non-streaming LLM call. Returns full response text."""
    system, chat_msgs = _extract_system(messages)
    client = _get_client()

    response = await client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system if system else "You are a helpful tutor.",
        messages=chat_msgs,
    )
    return response.content[0].text
