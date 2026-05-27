import pytest

from seekflow.repl.session import build_prompt_message, dispatch_input


@pytest.mark.asyncio
async def test_dispatches_slash_command() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("/help", fake_command, fake_search)
    assert calls == [("command", "/help")]


@pytest.mark.asyncio
async def test_dispatches_search_query() -> None:
    calls: list[tuple[str, str]] = []

    async def fake_command(text: str) -> None:
        calls.append(("command", text))

    async def fake_search(text: str) -> None:
        calls.append(("search", text))

    await dispatch_input("python gil", fake_command, fake_search)
    assert calls == [("search", "python gil")]


def test_build_prompt_message_looks_like_chat_input() -> None:
    prompt = build_prompt_message("Ask SeekFlow to research a topic...")
    assert "Ask SeekFlow to research a topic..." in prompt
    assert "╭" in prompt
    assert "╰─❯ " in prompt
