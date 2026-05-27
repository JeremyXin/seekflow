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


def build_prompt_message(
    placeholder: str = "Ask SeekFlow to research a topic...",
    hint: str = "Enter to search • /help for commands",
) -> str:
    content_width = max(len(placeholder), len(hint), 46)
    top = f"╭{'─' * (content_width + 2)}╮"
    line_one = f"│ {placeholder.ljust(content_width)} │"
    line_two = f"│ {hint.ljust(content_width)} │"
    bottom = "╰─❯ "
    return "\n".join([top, line_one, line_two, bottom])


async def repl_loop(config, command_handler, search_handler, session) -> None:
    while True:
        text = await session.prompt_async(build_prompt_message())
        if text.strip() in {"/exit", "/quit"}:
            break
        await dispatch_input(text, command_handler, search_handler)


def build_session(history_path) -> PromptSession:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return PromptSession(history=FileHistory(str(history_path)))
