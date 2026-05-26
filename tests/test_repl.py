import pytest

from seekflow.repl.session import dispatch_input


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
