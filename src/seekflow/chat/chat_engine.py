from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from seekflow.models import AppConfig, ConversationTurn


CHAT_SYSTEM_PROMPT = """You are SeekFlow in chat mode.
Answer conversationally. Do not claim to have searched the web unless search mode was used.
"""


def build_chat_messages(history: list[ConversationTurn], user_text: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    messages.append({"role": "user", "content": user_text})
    return messages


async def stream_chat_reply(
    user_text: str,
    history: list[ConversationTurn],
    config: AppConfig,
) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
    stream = await client.chat.completions.create(
        model=config.llm.model,
        stream=True,
        messages=build_chat_messages(history, user_text),
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta
