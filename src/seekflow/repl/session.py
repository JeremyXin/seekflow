from collections.abc import Awaitable, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


async def dispatch_input(
    text: str,
    command_handler: Callable[[str], Awaitable[None]],
    search_handler: Callable[[str], Awaitable[None]],
) -> None:
    stripped = text.strip()
    if not stripped:
        return
    if stripped.startswith("/"):
        await command_handler(stripped)
        return
    await search_handler(stripped)


async def repl_loop(config, command_handler, search_handler, session) -> None:
    while True:
        text = await session.prompt_async("seekflow> ")
        if text.strip() in {"/exit", "/quit"}:
            break
        await dispatch_input(text, command_handler, search_handler)


def build_session(history_path) -> PromptSession:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return PromptSession(history=FileHistory(str(history_path)))
