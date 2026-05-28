from dataclasses import dataclass
from pathlib import Path
import textwrap

from rich import box
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from seekflow import __version__
from seekflow.models import SearchResult


console = Console()


@dataclass(slots=True)
class SessionMessage:
    role: str
    title: str
    body: str


def build_ascii_logo() -> str:
    return (
        " ____             _     _____ _               \n"
        "/ ___|  ___  ___| | __|  ___| | _____      __\n"
        "\\___ \\ / _ \\/ _ \\ |/ /| |_  | |/ _ \\ \\ /\\ / /\n"
        " ___) |  __/  __/   < |  _| | | (_) \\ V  V / \n"
        "|____/ \\___|\\___|_|\\_\\|_|   |_|\\___/ \\_/\\_/  "
    )


def _collect_recent_activity(kb_dir: Path) -> str:
    entries = sorted(kb_dir.glob("**/*.md"))
    if not entries:
        return "No recent activity"
    latest = entries[-1]
    return f"{len(entries)} saved entries · latest: {latest.stem}"


def _clamp_text(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _wrap_lines(text: str, width: int) -> list[str]:
    wrapped = textwrap.wrap(text, width=max(width, 12)) or [""]
    return [_clamp_text(line, width) for line in wrapped]


def _pad_center(text: str, width: int) -> str:
    return _clamp_text(text, width).center(width)


def _pad_left(text: str, width: int) -> str:
    return _clamp_text(text, width).ljust(width)


def build_header_text(config, width: int = 108) -> str:
    inner_width = max(78, width - 2)
    divider = 3
    left_width = max(28, (inner_width - divider) // 2)
    right_width = inner_width - divider - left_width

    left_lines = [
        _pad_center("Welcome back!", left_width),
        _pad_center("seekflow", left_width),
        "",
        _pad_center(f"{config.llm.model} · {config.app.default_provider}", left_width),
        _pad_center(str(config.knowledge_base.kb_dir), left_width),
    ]
    right_lines = [
        *_wrap_lines("Tips for getting started", right_width),
        *_wrap_lines("Run /help to inspect commands", right_width),
        "─" * right_width,
        *_wrap_lines("Recent activity", right_width),
        *_wrap_lines(_collect_recent_activity(config.knowledge_base.kb_dir), right_width),
    ]
    rows = max(len(left_lines), len(right_lines))
    padded_left = left_lines + [""] * (rows - len(left_lines))
    padded_right = right_lines + [""] * (rows - len(right_lines))

    title = f" SeekFlow v{__version__} "
    top_fill = max(0, inner_width - len(title))
    top = "╭" + "─" * 3 + title + "─" * max(0, top_fill - 3) + "╮"
    middle = [
        f"│{_pad_left(left, left_width)} │ {_pad_left(right, right_width)}│"
        for left, right in zip(padded_left, padded_right, strict=False)
    ]
    bottom = "╰" + "─" * inner_width + "╯"
    return "\n".join([top, *middle, bottom])


def build_transcript_text(messages: list["SessionMessage"]) -> str:
    if not messages:
        return '  Try "compare asyncio vs threading in Python"'
    rendered_messages = messages
    blocks: list[str] = []
    for message in rendered_messages:
        body = message.body or " "
        if message.role == "user":
            blocks.append(f"› {body}")
            continue
        if message.role == "assistant":
            blocks.append(f"  {message.title or 'SeekFlow'}\n  {body}")
            continue
        if message.role == "tool":
            blocks.append(f"  {body}")
            continue
        if message.role == "sources":
            blocks.append(f"  Sources\n  {body}")
            continue
        if message.role == "saved":
            blocks.append(f"  Saved\n  {body}")
            continue
        if message.role == "error":
            blocks.append(f"  Warning\n  {body}")
            continue
        title = message.title or message.role.title()
        blocks.append(f"  {title}\n  {body}")
    return "\n\n".join(blocks)


def build_repl_body_text(config, messages: list["SessionMessage"], width: int = 108) -> str:
    return f"{build_header_text(config, width=width)}\n\n{build_transcript_text(messages)}"


def _render_left_header(config) -> RenderableType:
    return Group(
        Text("Welcome", style="bold cyan"),
        Text(build_ascii_logo(), style="bold white"),
        Text(f"v{__version__}", style="bright_black"),
        Text(f"provider: {config.app.default_provider}", style="white"),
        Text(f"model: {config.llm.model}", style="white"),
    )


def _render_right_header(config) -> RenderableType:
    return Group(
        Text("Session", style="bold cyan"),
        Text("Tips: use /provider list to inspect engines and /kb list to browse saved notes.", style="white"),
        Text(f"Recent activity: {_collect_recent_activity(config.knowledge_base.kb_dir)}", style="white"),
        Text(f"Knowledge base: {config.knowledge_base.kb_dir}", style="white"),
    )


def _render_message(message: SessionMessage) -> Panel:
    style_map = {
        "user": ("You", "bright_blue"),
        "assistant": ("SeekFlow", "white"),
        "tool": ("Web Search", "cyan"),
        "error": ("Error", "red"),
        "system": ("System", "bright_black"),
        "sources": ("Sources", "yellow"),
        "saved": ("Saved", "green"),
    }
    fallback_title, border_style = style_map.get(message.role, (message.title, "white"))
    title = message.title or fallback_title
    return Panel(
        Text(message.body or " ", style="white"),
        title=title,
        title_align="left",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def build_sources_message(results: list[SearchResult]) -> SessionMessage:
    if not results:
        return SessionMessage(role="sources", title="Sources", body="No sources")
    body = "\n".join(f"[{index}] {item.title}\n{item.url}" for index, item in enumerate(results, start=1))
    return SessionMessage(role="sources", title="Sources", body=body)


def build_saved_message(path: Path) -> SessionMessage:
    return SessionMessage(role="saved", title="Saved", body=f"Saved to {path}")


def build_error_message(message: str, suggestion: str | None = None) -> SessionMessage:
    body = message
    if suggestion:
        body = f"{body}\n{suggestion}"
    return SessionMessage(role="error", title="Error", body=body)


def build_app_shell(config, messages: list[SessionMessage]) -> RenderableType:
    header = Panel(
        Columns(
            [
                Panel(_render_left_header(config), border_style="cyan", box=box.ROUNDED),
                Panel(_render_right_header(config), border_style="cyan", box=box.ROUNDED),
            ],
            equal=True,
            expand=True,
        ),
        title=f"SeekFlow v{__version__}",
        title_align="left",
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(1, 1),
    )

    rendered_messages = messages[-10:] if messages else [SessionMessage(role="system", title="System", body='Try "compare asyncio vs threading in Python"')]
    message_group = Group(*[_render_message(message) for message in rendered_messages])
    body = Panel(
        message_group,
        title="Conversation",
        title_align="left",
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(1, 1),
    )

    return Group(header, body)


def render_app_shell(config, messages: list[SessionMessage]) -> None:
    console.print(build_app_shell(config, messages))


def show_info(message: str) -> None:
    console.print(message)


def show_error(message: str, suggestion: str | None = None) -> None:
    console.print(f"[red]{message}[/red]")
    if suggestion:
        console.print(f"[blue]{suggestion}[/blue]")


def show_sources(results: list[SearchResult]) -> None:
    for index, result in enumerate(results, start=1):
        console.print(f"[cyan][{index}][/cyan] {result.title} - {result.url}")


def show_saved_path(path) -> None:
    console.print(f"[green]Saved to {path}[/green]")
